from django.contrib.postgres.aggregates import JSONBAgg, StringAgg
from django.core.exceptions import FieldError
from django.db.models import (
    CharField,
    Count,
    F,
    Func,
    IntegerField,
    JSONField,
    Min,
    Q,
    Value,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Coalesce, Concat, Trim

from attendees.occasions.models import Gathering, Meet
from attendees.persons.models import Attendee, AttendingMeet, FolkAttendee


class RosterService:
    @staticmethod
    def get_roster_data(
        organization,
        meet_slugs,
        start,
        finish,
        skip,
        take,
        sort_list=None,
        search_value=None,
        extra_filters=None,
        current_user=None,
        columns=None,
    ):
        if not sort_list:
            sort_list = ['first_name', 'last_name']

        # 1. Query Gatherings (Columns)
        gatherings = Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization=organization,
            start__gte=start,
            finish__lte=finish,
            is_removed=False
        ).order_by('start', 'meet__display_name', 'id')

        if columns is None:
            columns = [
                {
                    "id": g.id,
                    "display_name": g.display_name,
                    "start": g.start.isoformat() if g.start else None,
                    "finish": g.finish.isoformat() if g.finish else None,
                    "meet_id": g.meet_id,
                    "meet_display_name": g.meet.display_name if g.meet else "",
                    "attendances_count": getattr(g, 'attendances_count', 0),
                    "enrolled_count": getattr(g, 'enrolled_count', 0),
                    "_start_dt": g.start,
                }
                for g in gatherings
            ]

        # 2. Query Attendees (Rows) with Database Aggregation
        attendingmeet_filter = (
            Q(attendings__attendingmeet__meet__slug__in=meet_slugs) &
            Q(attendings__attendingmeet__is_removed=False) &
            Q(attendings__is_removed=False) &
            (Q(attendings__attendingmeet__finish__isnull=True) | Q(attendings__attendingmeet__finish__gte=start)) &
            (Q(attendings__attendingmeet__start__isnull=True) | Q(attendings__attendingmeet__start__lte=finish))
        )

        attendees_qs = Attendee.objects.filter(
            attendingmeet_filter,
            is_removed=False
        )

        if current_user and not current_user.can_see_all_organizational_meets_attendees():
            user_attendee = getattr(current_user, "attendee", None)
            if not user_attendee:
                return columns, [], 0
            user_folk_ids = list(
                user_attendee.folks.filter(
                    is_removed=False,
                    folkattendee__is_removed=False,
                ).values_list("id", flat=True)
            )
            attendees_qs = attendees_qs.filter(
                Q(folkattendee__folk__in=user_folk_ids, folkattendee__is_removed=False) |
                Q(id=user_attendee.id)
            )

        if search_value:
            clean_search_value = " ".join(search_value.split())
            attendees_qs = attendees_qs.annotate(
                _search_full_name=Trim(
                    Concat(
                        Trim(Concat('first_name', Value(' '), 'last_name', output_field=CharField())),
                        Value(' '),
                        Trim(Concat('last_name2', 'first_name2', output_field=CharField())),
                        output_field=CharField()
                    )
                )
            )
            search_filter = (
                Q(_search_full_name__icontains=clean_search_value) |
                Q(first_name__icontains=clean_search_value) |
                Q(last_name__icontains=clean_search_value) |
                Q(first_name2__icontains=clean_search_value) |
                Q(last_name2__icontains=clean_search_value) |
                Q(infos__names__original__icontains=clean_search_value) |
                Q(infos__contacts__icontains=clean_search_value) |
                Q(infos__icontains=clean_search_value) |
                Q(attendings__attendingmeet__team__display_name__icontains=clean_search_value) |
                Q(attendings__attendingmeet__character__display_name__icontains=clean_search_value)
            )
            attendees_qs = attendees_qs.filter(search_filter)

        normalized_sort_list = []
        for s in sort_list:
            if s.startswith('-attendee__'):
                normalized_sort_list.append('-' + s[11:])
            elif s.startswith('attendee__'):
                normalized_sort_list.append(s[10:])
            elif s in ('team__display_order', 'team__display_name', 'team'):
                normalized_sort_list.append(F('team__display_order').asc(nulls_last=True))
                normalized_sort_list.append('team__display_name')
            elif s in ('-team__display_order', '-team__display_name', '-team'):
                normalized_sort_list.append(F('team__display_order').desc(nulls_last=True))
                normalized_sort_list.append('-team__display_name')
            elif s in ('character__display_name', 'character'):
                normalized_sort_list.append('character__display_name')
            elif s in ('-character__display_name', '-character'):
                normalized_sort_list.append('-character__display_name')
            elif s == 'grade':
                normalized_sort_list.append(F('grade').asc(nulls_last=True))
            elif s == '-grade':
                normalized_sort_list.append(F('grade').desc(nulls_last=True))
            else:
                normalized_sort_list.append(s)

        attendees_qs = attendees_qs.annotate(
            grade=Coalesce(
                Cast(KeyTextTransform('grade', KeyTextTransform('fixed', 'infos')), output_field=IntegerField()),
                Cast(KeyTextTransform('grade', 'infos'), output_field=IntegerField())
            ),
            team__display_name=StringAgg(
                'attendings__attendingmeet__team__display_name',
                delimiter=', ',
                distinct=True,
                filter=attendingmeet_filter,
                default=None,
            ),
            team__display_order=Min(
                'attendings__attendingmeet__team__display_order',
                filter=attendingmeet_filter,
            ),
            character__display_name=StringAgg(
                'attendings__attendingmeet__character__display_name',
                delimiter=', ',
                distinct=True,
                filter=attendingmeet_filter,
                default=None,
            ),
            total_attendances=Count(
                'attendings__attendance',
                filter=Q(
                    attendings__attendance__gathering__in=gatherings,
                    attendings__attendance__is_removed=False
                ) & ~Q(attendings__attendance__category_id=1),
                distinct=True
            ),
            attendances=Coalesce(JSONBAgg(
                Func(
                    Value('attendance_id'), 'attendings__attendance__id',
                    Value('attending_id'), 'attendings__attendance__attending__id',
                    Value('category_id'), 'attendings__attendance__category__id',
                    Value('category_name'), 'attendings__attendance__category__display_name',
                    Value('gathering_id'), 'attendings__attendance__gathering__id',
                    Value('start'), 'attendings__attendance__start',
                    Value('finish'), 'attendings__attendance__finish',
                    Value('file_path'), 'attendings__attendance__file',
                    function='jsonb_build_object',
                ),
                filter=Q(attendings__attendance__gathering__in=gatherings, attendings__attendance__is_removed=False),
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
            attendingmeets=Coalesce(JSONBAgg(
                Func(
                    Value('attending_id'), 'attendings__attendingmeet__attending_id',
                    Value('attendingmeet_id'), 'attendings__attendingmeet__id',
                    Value('meet_id'), 'attendings__attendingmeet__meet_id',
                    Value('meet_name'), 'attendings__attendingmeet__meet__display_name',
                    Value('character_id'), 'attendings__attendingmeet__character_id',
                    Value('character_name'), 'attendings__attendingmeet__character__display_name',
                    Value('team_id'), 'attendings__attendingmeet__team_id',
                    Value('team_name'), 'attendings__attendingmeet__team__display_name',
                    Value('start'), 'attendings__attendingmeet__start',
                    Value('finish'), 'attendings__attendingmeet__finish',
                    Value('infos'), 'attendings__attendingmeet__infos',
                    function='jsonb_build_object',
                ),
                filter=attendingmeet_filter,
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
        ).distinct().order_by(*normalized_sort_list)

        if extra_filters:
            try:
                filtered_qs = attendees_qs.filter(extra_filters)
                total_count = filtered_qs.count()
                attendees_qs = filtered_qs
            except (FieldError, ValueError):
                total_count = attendees_qs.count()
        else:
            total_count = attendees_qs.count()

        attendees_page = attendees_qs[skip: skip + take]

        # 3. If kid meet, resolve siblings (display_order >= 10) in 2 O(N) passes using dictionary
        meets = list(Meet.objects.filter(slug__in=meet_slugs, is_removed=False).select_related("assembly__division"))
        kid_meet_major_chars = {}
        for m in meets:
            m_is_kid = bool(
                (m.assembly and m.assembly.division and m.assembly.division.infos and (
                    m.assembly.division.infos.get("show_attendee_infos", {}).get("infos-grade")
                    or m.assembly.division.infos.get("show_attendee_infos", {}).get("grade")
                ))
                or (m.infos and m.infos.get("kid_search_families_show_grades"))
            )
            if m_is_kid and m.major_character_id:
                kid_meet_major_chars[m.id] = m.major_character_id

        def is_student_attendee(att):
            for am in (getattr(att, 'attendingmeets', None) or []):
                m_id = am.get('meet_id')
                char_id = am.get('character_id')
                if m_id in kid_meet_major_chars and str(char_id) == str(kid_meet_major_chars[m_id]):
                    return True
            return False

        siblings_by_attendee = {}
        parents_by_attendee = {}
        if kid_meet_major_chars and attendees_page:
            student_attendees = [a for a in attendees_page if is_student_attendee(a)]
            if student_attendees:
                page_att_ids = [a.id for a in student_attendees]
                page_fa_rows = list(
                    FolkAttendee.objects.filter(
                        attendee_id__in=page_att_ids,
                        folk__category_id=Attendee.FAMILY_CATEGORY,
                        folk__is_removed=False,
                        is_removed=False,
                    ).values("attendee_id", "folk_id")
                )

                attendee_to_folk_ids = {}
                all_family_folk_ids = set()
                for r in page_fa_rows:
                    attendee_to_folk_ids.setdefault(r["attendee_id"], set()).add(r["folk_id"])
                    all_family_folk_ids.add(r["folk_id"])

                if all_family_folk_ids:
                    sibling_fas = list(
                        FolkAttendee.objects.filter(
                            folk_id__in=all_family_folk_ids,
                            folk__category_id=Attendee.FAMILY_CATEGORY,
                            folk__is_removed=False,
                            is_removed=False,
                            attendee__is_removed=False,
                            role__relative=True,
                        )
                        .filter(
                            Q(role__title__in=["son", "daughter", "child", "ward"])
                            | Q(role__title__icontains="brother")
                            | Q(role__title__icontains="sister")
                            | Q(role__title__icontains="sibling")
                            | Q(display_order__gte=10)
                        )
                        .values(
                            "folk_id",
                            "attendee_id",
                            "attendee__first_name",
                            "attendee__last_name",
                            "attendee__first_name2",
                            "attendee__last_name2",
                        )
                        .distinct()
                    )

                    sibling_att_ids = {s["attendee_id"] for s in sibling_fas}

                    enrolled_sibling_ids = set(
                        AttendingMeet.objects.filter(
                            attending__attendee_id__in=sibling_att_ids,
                            meet__slug__in=meet_slugs,
                            is_removed=False,
                            attending__is_removed=False,
                        )
                        .filter(
                            Q(finish__isnull=True) | Q(finish__gte=start)
                        )
                        .filter(
                            Q(start__isnull=True) | Q(start__lte=finish)
                        )
                        .values_list("attending__attendee_id", flat=True)
                        .distinct()
                    )

                    # Pass 1: Build folk_id -> siblings dictionary
                    folk_to_siblings = {}
                    for s in sibling_fas:
                        f_id = s["folk_id"]
                        att_id = s["attendee_id"]
                        fn = (s["attendee__first_name"] or "").strip()
                        ln = (s["attendee__last_name"] or "").strip()
                        fn2 = (s["attendee__first_name2"] or "").strip()
                        ln2 = (s["attendee__last_name2"] or "").strip()
                        name1 = f"{fn} {ln}".strip()
                        name2 = f"{ln2}{fn2}".strip()
                        name = f"{name1} {name2}".strip() if (name1 and name2) else (name1 or name2 or "Unknown")
                        is_enrolled = att_id in enrolled_sibling_ids
                        folk_to_siblings.setdefault(f_id, []).append({
                            "id": str(att_id),
                            "name": name,
                            "attending": is_enrolled,
                        })

                    # Pass 2: Map siblings to each student attendee in current page (O(1) per attendee)
                    for a in student_attendees:
                        a_folk_ids = attendee_to_folk_ids.get(a.id, set())
                        seen_sibling_ids = {str(a.id)}
                        att_siblings = []
                        for f_id in a_folk_ids:
                            for sib in folk_to_siblings.get(f_id, []):
                                if sib["id"] not in seen_sibling_ids:
                                    seen_sibling_ids.add(sib["id"])
                                    att_siblings.append(sib)
                        siblings_by_attendee[a.id] = att_siblings

                    # Parents resolution: Adults with parental/guardian roles in the student's family
                    parent_fas = list(
                        FolkAttendee.objects.filter(
                            folk_id__in=all_family_folk_ids,
                            folk__category_id=Attendee.FAMILY_CATEGORY,
                            folk__is_removed=False,
                            is_removed=False,
                            attendee__is_removed=False,
                        )
                        .filter(
                            Q(role__title__in=["father", "mother", "parent", "guardian", "caregiver", "husband", "wife", "spouse"])
                            | Q(role__scheduler=True)
                        )
                        .values(
                            "folk_id",
                            "attendee_id",
                            "attendee__first_name",
                            "attendee__last_name",
                            "attendee__first_name2",
                            "attendee__last_name2",
                            "attendee__infos",
                            "role__title",
                            "display_order",
                        )
                        .distinct()
                    )

                    folk_to_parents = {}
                    for p in parent_fas:
                        f_id = p["folk_id"]
                        att_id = p["attendee_id"]
                        p_infos = p.get("attendee__infos") or {}
                        contacts_dict = {}
                        if isinstance(p_infos, dict):
                            contacts_dict = p_infos.get("contacts") or {}

                        contacts_parts = []
                        if isinstance(contacts_dict, dict):
                            for k, v in contacts_dict.items():
                                if v:
                                    contacts_parts.append(str(v))
                        contacts_str = ", ".join(contacts_parts)

                        fn = (p["attendee__first_name"] or "").strip()
                        ln = (p["attendee__last_name"] or "").strip()
                        fn2 = (p["attendee__first_name2"] or "").strip()
                        ln2 = (p["attendee__last_name2"] or "").strip()
                        name1 = f"{fn} {ln}".strip()
                        name2 = f"{ln2}{fn2}".strip()
                        name = f"{name1} {name2}".strip() if (name1 and name2) else (name1 or name2 or "Parent")

                        folk_to_parents.setdefault(f_id, []).append({
                            "id": str(att_id),
                            "name": name,
                            "role": p.get("role__title") or "",
                            "display_order": p.get("display_order") or 0,
                            "contacts": contacts_str,
                            "infos_contacts": contacts_dict if isinstance(contacts_dict, dict) else {},
                        })

                    for a in student_attendees:
                        a_folk_ids = attendee_to_folk_ids.get(a.id, set())
                        seen_parent_ids = {str(a.id)}
                        att_parents = []
                        for f_id in a_folk_ids:
                            for p in folk_to_parents.get(f_id, []):
                                if p["id"] not in seen_parent_ids:
                                    seen_parent_ids.add(p["id"])
                                    att_parents.append(p)
                        att_parents.sort(key=lambda x: x.get("display_order") or 0)
                        parents_by_attendee[a.id] = att_parents

        # 4. Build Response
        rows = []
        for attendee in attendees_page:
            photo_url = None
            if attendee.photo:
                try:
                    photo_url = attendee.photo.url
                except ValueError:
                    pass

            primary_attending_id = attendee.attendingmeets[0]['attending_id'] if attendee.attendingmeets else None

            contacts_dict = attendee.infos.get('contacts', {}) if isinstance(attendee.infos, dict) else {}
            contacts_parts = []
            if isinstance(contacts_dict, dict):
                for k, v in contacts_dict.items():
                    if v:
                        contacts_parts.append(str(v))
            contacts_str = ", ".join(contacts_parts)

            grade = None
            if isinstance(attendee.infos, dict):
                fixed = attendee.infos.get('fixed')
                if isinstance(fixed, dict) and 'grade' in fixed:
                    grade = fixed['grade']
                elif 'grade' in attendee.infos:
                    grade = attendee.infos['grade']

            rows.append({
                "attending_id": primary_attending_id,
                "attendee_id": attendee.id,
                "attendee_name": attendee.display_label,
                "photo_url": photo_url,
                "team__display_name": attendee.team__display_name,
                "team__display_order": attendee.team__display_order,
                "character__display_name": attendee.character__display_name,
                "grade": grade,
                "contacts": contacts_str,
                "infos_contacts": contacts_dict,
                "attendances": attendee.attendances,
                "attendingmeets": attendee.attendingmeets,
                "total_attendances": attendee.total_attendances,
                "siblings": siblings_by_attendee.get(attendee.id, []),
                "parents": parents_by_attendee.get(attendee.id, []),
            })

        return columns, rows, total_count

    @staticmethod
    def _parse_numeric_filter(target_field, operator, val, is_nullable=True):
        if val is None or val == "":
            if operator == "=":
                return Q(**{f"{target_field}__isnull": True}) if is_nullable else Q(id__isnull=True)
            elif operator == "<>":
                return Q(**{f"{target_field}__isnull": False}) if is_nullable else ~Q(id__isnull=True)
            return Q()

        try:
            int_val = int(float(val))
        except (ValueError, TypeError):
            if operator in ("=", "contains", "startswith", "endswith", ">", ">=", "<", "<="):
                return Q(id__isnull=True)
            elif operator in ("<>", "notcontains"):
                return Q(**{f"{target_field}__isnull": False}) if is_nullable else ~Q(id__isnull=True)
            return Q(id__isnull=True)

        if operator in ("=", "contains"):
            return Q(**{target_field: int_val})
        elif operator in ("<>", "notcontains"):
            return ~Q(**{target_field: int_val})
        elif operator == ">":
            return Q(**{f"{target_field}__gt": int_val})
        elif operator == ">=":
            return Q(**{f"{target_field}__gte": int_val})
        elif operator == "<":
            return Q(**{f"{target_field}__lt": int_val})
        elif operator == "<=":
            return Q(**{f"{target_field}__lte": int_val})
        return Q(**{target_field: int_val})

    @staticmethod
    def parse_filter_expr(expr):
        if not expr:
            return Q()
        if isinstance(expr, list):
            while len(expr) == 1 and isinstance(expr[0], list):
                expr = expr[0]
            if not expr:
                return Q()
            if expr[0] == "!":
                return ~RosterService.parse_filter_expr(expr[1])
            if len(expr) >= 3 and any(op in expr for op in ("and", "or")):
                op = "or" if "or" in expr else "and"
                clauses = [e for e in expr if e != op]
                res = RosterService.parse_filter_expr(clauses[0])
                for c in clauses[1:]:
                    sub_q = RosterService.parse_filter_expr(c)
                    if op == "or":
                        res = res | sub_q
                    else:
                        res = res & sub_q
                return res
            if len(expr) == 3 and isinstance(expr[1], str):
                field, operator, val = expr[0], expr[1].lower(), expr[2]
                if field in ("team", "team__display_name"):
                    target_field = "attendings__attendingmeet__team__display_name" if operator == "contains" else "team__display_name"
                elif field in ("character", "character__display_name"):
                    target_field = "attendings__attendingmeet__character__display_name" if operator == "contains" else "character__display_name"
                elif field == "grade":
                    return RosterService._parse_numeric_filter("grade", operator, val, is_nullable=True)
                elif field == "total_attendances":
                    return RosterService._parse_numeric_filter("total_attendances", operator, val, is_nullable=False)
                elif field in ("attendee_id", "id"):
                    return RosterService._parse_numeric_filter("id", operator, val, is_nullable=False)
                elif field == "attending_id":
                    return RosterService._parse_numeric_filter("attendings__id", operator, val, is_nullable=False)
                elif field in ("gender",):
                    return RosterService._parse_numeric_filter("gender", operator, val, is_nullable=True)
                elif field == "attendee_name":
                    parts = str(val).split() if val else []
                    if operator == "contains":
                        name_q = (
                            Q(first_name__icontains=val) |
                            Q(last_name__icontains=val) |
                            Q(first_name2__icontains=val) |
                            Q(last_name2__icontains=val) |
                            Q(infos__names__original__icontains=val)
                        )
                        if len(parts) >= 2:
                            name_q |= (
                                (Q(first_name__icontains=parts[0]) & Q(last_name__icontains=parts[-1])) |
                                (Q(last_name__icontains=parts[0]) & Q(first_name__icontains=parts[-1])) |
                                (Q(first_name2__icontains=parts[0]) & Q(last_name2__icontains=parts[-1])) |
                                (Q(last_name2__icontains=parts[0]) & Q(first_name2__icontains=parts[-1]))
                            )
                        return name_q
                    elif operator == "=":
                        return (
                            Q(first_name=val) |
                            Q(last_name=val) |
                            Q(infos__names__original=val)
                        )
                    return Q()
                elif field in ("contacts", "infos_contacts"):
                    if operator == "contains":
                        return Q(infos__contacts__icontains=val) | Q(infos__icontains=val)
                    elif operator == "notcontains":
                        return ~(Q(infos__contacts__icontains=val) | Q(infos__icontains=val))
                    elif operator == "=":
                        if val is None or val == "":
                            return Q(infos__contacts__isnull=True) | Q(infos__isnull=True)
                        return Q(infos__contacts__icontains=val)
                    elif operator == "<>":
                        if val is None or val == "":
                            return Q(infos__contacts__isnull=False) & ~Q(infos__isnull=True)
                        return ~Q(infos__contacts__icontains=val)
                    return Q()
                elif field in ("siblings", "parents", "attendances", "attendingmeets", "photo_url"):
                    return Q()
                else:
                    target_field = field

                if operator == "=":
                    if val is None or val == "":
                        return Q(**{f"{target_field}__isnull": True}) | Q(**{target_field: ""})
                    return Q(**{target_field: val})
                elif operator == "<>":
                    if val is None or val == "":
                        return Q(**{f"{target_field}__isnull": False}) & ~Q(**{target_field: ""})
                    return ~Q(**{target_field: val})
                elif operator == "contains":
                    return Q(**{f"{target_field}__icontains": val})
                elif operator == "notcontains":
                    return ~Q(**{f"{target_field}__icontains": val})
                elif operator == "startswith":
                    return Q(**{f"{target_field}__istartswith": val})
                elif operator == "endswith":
                    return Q(**{f"{target_field}__iendswith": val})
                elif operator == ">":
                    return Q(**{f"{target_field}__gt": val})
                elif operator == ">=":
                    return Q(**{f"{target_field}__gte": val})
                elif operator == "<":
                    return Q(**{f"{target_field}__lt": val})
                elif operator == "<=":
                    return Q(**{f"{target_field}__lte": val})
        return Q()

    @staticmethod
    def extract_search_value(filter_expr):
        if not filter_expr or not isinstance(filter_expr, list):
            return None
        while len(filter_expr) == 1 and isinstance(filter_expr[0], list):
            filter_expr = filter_expr[0]
        if len(filter_expr) == 3 and isinstance(filter_expr[1], str) and filter_expr[1].lower() == "contains" and isinstance(filter_expr[2], str):
            return filter_expr[2]
        for item in filter_expr:
            if isinstance(item, list):
                val = RosterService.extract_search_value(item)
                if val:
                    return val
        return None

    @staticmethod
    def get_roster_group_counts(
        organization,
        meet_slugs,
        start,
        finish,
        group_column,
        group_desc=False,
        search_value=None,
        extra_filters=None,
        current_user=None,
    ):
        attendingmeet_filter = (
            Q(attendings__attendingmeet__meet__slug__in=meet_slugs) &
            Q(attendings__attendingmeet__is_removed=False) &
            Q(attendings__is_removed=False) &
            (Q(attendings__attendingmeet__finish__isnull=True) | Q(attendings__attendingmeet__finish__gte=start)) &
            (Q(attendings__attendingmeet__start__isnull=True) | Q(attendings__attendingmeet__start__lte=finish))
        )

        attendees_qs = Attendee.objects.filter(
            attendingmeet_filter,
            is_removed=False
        )

        if current_user and not current_user.can_see_all_organizational_meets_attendees():
            user_attendee = getattr(current_user, "attendee", None)
            if not user_attendee:
                return []
            user_folk_ids = list(
                user_attendee.folks.filter(
                    is_removed=False,
                    folkattendee__is_removed=False,
                ).values_list("id", flat=True)
            )
            attendees_qs = attendees_qs.filter(
                Q(folkattendee__folk__in=user_folk_ids, folkattendee__is_removed=False) |
                Q(id=user_attendee.id)
            )

        if search_value:
            clean_search_value = " ".join(search_value.split())
            attendees_qs = attendees_qs.annotate(
                _search_full_name=Trim(
                    Concat(
                        Trim(Concat('first_name', Value(' '), 'last_name', output_field=CharField())),
                        Value(' '),
                        Trim(Concat('last_name2', 'first_name2', output_field=CharField())),
                        output_field=CharField()
                    )
                )
            )
            search_filter = (
                Q(_search_full_name__icontains=clean_search_value) |
                Q(first_name__icontains=clean_search_value) |
                Q(last_name__icontains=clean_search_value) |
                Q(first_name2__icontains=clean_search_value) |
                Q(last_name2__icontains=clean_search_value) |
                Q(infos__names__original__icontains=clean_search_value) |
                Q(infos__contacts__icontains=clean_search_value) |
                Q(infos__icontains=clean_search_value) |
                Q(attendings__attendingmeet__team__display_name__icontains=clean_search_value) |
                Q(attendings__attendingmeet__character__display_name__icontains=clean_search_value)
            )
            attendees_qs = attendees_qs.filter(search_filter)

        if extra_filters:
            try:
                attendees_qs = attendees_qs.filter(extra_filters)
            except (FieldError, ValueError):
                pass

        if group_column in ("team__display_name", "team"):
            db_field = 'attendings__attendingmeet__team__display_name'
            if group_desc:
                order_exprs = [F('team_order').desc(nulls_last=True), f"-{db_field}"]
            else:
                order_exprs = [F('team_order').asc(nulls_last=True), db_field]
            counters = list(
                attendees_qs.values(db_field)
                .annotate(
                    count=Count('id', distinct=True),
                    team_order=Min('attendings__attendingmeet__team__display_order')
                )
                .order_by(*order_exprs)
            )
            return [
                {group_column: item[db_field], 'count': item['count']}
                for item in counters
            ]

        if group_column in ("character__display_name", "character"):
            db_field = 'attendings__attendingmeet__character__display_name'
            order_field = f"-{db_field}" if group_desc else db_field
            counters = list(
                attendees_qs.values(db_field)
                .annotate(count=Count('id', distinct=True))
                .order_by(order_field)
            )
            return [
                {group_column: item[db_field], 'count': item['count']}
                for item in counters
            ]

        if group_column == "grade":
            attendees_qs = attendees_qs.annotate(
                grade=Coalesce(
                    Cast(KeyTextTransform('grade', KeyTextTransform('fixed', 'infos')), output_field=IntegerField()),
                    Cast(KeyTextTransform('grade', 'infos'), output_field=IntegerField())
                )
            )
            order_field = "-grade" if group_desc else "grade"
            counters = list(
                attendees_qs.values('grade')
                .annotate(count=Count('id', distinct=True))
                .order_by(order_field)
            )
            return [
                {'grade': item['grade'], 'count': item['count']}
                for item in counters
            ]

        if group_column == "attendee_name":
            attendees_qs = attendees_qs.annotate(
                attendee_name=Trim(
                    Concat(
                        Trim(Concat('first_name', Value(' '), 'last_name', output_field=CharField())),
                        Value(' '),
                        Trim(Concat('last_name2', 'first_name2', output_field=CharField())),
                        output_field=CharField()
                    )
                )
            )
            order_field = "-attendee_name" if group_desc else "attendee_name"
            counters = list(
                attendees_qs.values('attendee_name')
                .annotate(count=Count('id', distinct=True))
                .order_by(order_field)
            )
            return [
                {'attendee_name': item['attendee_name'], 'count': item['count']}
                for item in counters
            ]

        order_field = f"-{group_column}" if group_desc else group_column
        counters = list(
            attendees_qs.values(group_column)
            .annotate(count=Count('id', distinct=True))
            .order_by(order_field)
        )
        return [
            {group_column: item[group_column], 'count': item['count']}
            for item in counters
        ]
