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

from attendees.occasions.models import Gathering
from attendees.persons.models import Attendee


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

        # 3. Build Response
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
            })

        return columns, rows, total_count
