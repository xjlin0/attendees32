from django.contrib.postgres.aggregates import JSONBAgg, StringAgg
from django.db.models import (
    CharField,
    Count,
    F,
    Func,
    JSONField,
    Min,
    Q,
    Value,
)
from django.db.models.functions import Coalesce, Concat, Trim

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
                    "meet_id": g.meet_id,
                    "meet_display_name": g.meet.display_name if g.meet else "",
                    "attendances_count": getattr(g, 'attendances_count', 0),
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
            else:
                normalized_sort_list.append(s)

        attendees_qs = attendees_qs.annotate(
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

        total_count = attendees_qs.count()
        attendees_page = attendees_qs[skip: skip + take]

        # 3. If kid meet, resolve siblings (display_order >= 10) in 2 O(N) passes using dictionary
        meets = list(Meet.objects.filter(slug__in=meet_slugs, is_removed=False).select_related("assembly__division"))
        is_kid_meet = any(
            bool(
                (m.assembly and m.assembly.division and m.assembly.division.infos and (
                    m.assembly.division.infos.get("show_attendee_infos", {}).get("infos-grade")
                    or m.assembly.division.infos.get("show_attendee_infos", {}).get("grade")
                ))
                or (m.infos and m.infos.get("kid_search_families_show_grades"))
            )
            for m in meets
        )

        siblings_by_attendee = {}
        if is_kid_meet and attendees_page:
            page_att_ids = [a.id for a in attendees_page]
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

                # Pass 2: Map siblings to each attendee in current page (O(1) per attendee)
                for a in attendees_page:
                    a_folk_ids = attendee_to_folk_ids.get(a.id, set())
                    seen_sibling_ids = {str(a.id)}
                    att_siblings = []
                    for f_id in a_folk_ids:
                        for sib in folk_to_siblings.get(f_id, []):
                            if sib["id"] not in seen_sibling_ids:
                                seen_sibling_ids.add(sib["id"])
                                att_siblings.append(sib)
                    siblings_by_attendee[a.id] = att_siblings

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

            rows.append({
                "attending_id": primary_attending_id,
                "attendee_id": attendee.id,
                "attendee_name": attendee.display_label,
                "photo_url": photo_url,
                "team__display_name": attendee.team__display_name,
                "team__display_order": attendee.team__display_order,
                "character__display_name": attendee.character__display_name,
                "contacts": contacts_str,
                "attendances": attendee.attendances,
                "attendingmeets": attendee.attendingmeets,
                "total_attendances": attendee.total_attendances,
                "siblings": siblings_by_attendee.get(attendee.id, []),
            })

        return columns, rows, total_count
