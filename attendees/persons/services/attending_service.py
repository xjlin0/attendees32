from datetime import datetime, timezone

from django.db.models import Q, Value, Count, Func, JSONField
from django.db.models.expressions import F
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import JSONBAgg, StringAgg

from attendees.occasions.models import Attendance, Gathering
from attendees.persons.models import Attending, Attendee


class AttendingService:
    @staticmethod
    def by_organization_meets_gatherings(
        meet_slugs, user_attended_gathering_ids, user_organization_slug
    ):
        """
        :query: Find all gatherings of the current user, then list all attendings of the found gatherings.
                So if the current user didn't participate(attending), no info will be shown
        :param meet_slugs: slugs of the meets to be filtered
        :param user_attended_gathering_ids: primary gathering id of the Attendings to be filtered
        :param user_organization_slug: slugs of the user organization to be filtered
        :return: all Attendings with participating meets(group) and character(role)
        """
        return (
            Attending.objects.select_related()
            .prefetch_related()
            .filter(
                # registration_start/finish within the selected time period.
                meets__slug__in=meet_slugs,
                gathering__id__in=user_attended_gathering_ids,
                meets__assembly__division__organization__slug=user_organization_slug,
            )
            .annotate(
                meet=F("attendingmeet__meet__display_name"),
                character=F("attendingmeet__character__display_name"),
            )
            .order_by(
                "attendee",
            )
            .distinct()
        )

    @staticmethod
    def by_family_organization_attendings(
        attendee, current_user_organization, meet_slugs
    ):
        """
        :query: Find all gatherings of the current user and their kids/care-receivers, then list all attendings of the
                found gatherings. So if the current user didn't participate(attending), no info will be shown.
        :param attendee: logged in user's attendee or attendee to be checked by data_admins
        :param current_user_organization current_user_organization
        :param meet_slugs: slugs of the meets to be filtered
        :return: all Attendings with participating meets(group) and character(role)
        """
        return (
            Attending.objects.select_related()
            .prefetch_related()
            .filter(
                Q(attendee=attendee),
                # |
                # Q(attendee__in=attendee.related_ones.filter(
                #     from_attendee__scheduler=True,
                # )),
                meets__slug__in=meet_slugs,
                meets__assembly__division__organization=current_user_organization,
            )
            .annotate(
                meet=F("attendingmeet__meet__display_name"),
                character=F("attendingmeet__character__display_name"),
            )
            .order_by(
                "attendee",
            )
        )  # Todo: filter by start/finish within the selected time period.

    @staticmethod
    def by_assembly_meet_characters(assembly_slug, meet_slugs, character_slugs):
        """
        :param assembly_slug:
        :param meet_slugs:
        :param character_slugs:
        :return:
        """
        return (
            Attending.objects.select_related()
            .prefetch_related()
            .filter(
                meets__slug__in=meet_slugs,
                attendingmeet__character__slug__in=character_slugs,
                meets__assembly__slug=assembly_slug,
            )
            .distinct()
        )

    @staticmethod
    def end_all_activities(attending):
        now = datetime.now(timezone.utc)
        ongoing_attendingmeets = attending.attendingmeet_set.filter(
            Q(finish__isnull=True) | Q(finish__gte=now)
        )
        ongoing_attendingmeets.update(finish=now)
        for ongoing_attendingmeet in ongoing_attendingmeets:
            Attendance.objects.filter(
                (Q(finish__isnull=True) | Q(finish__gte=now)),
                gathering__meet=ongoing_attendingmeet.meet,
                attending=ongoing_attendingmeet.attending,
            ).update(finish=now)

    @staticmethod
    def destroy_with_associations(attending):
        """
        No permission check, delete the attending with attendingmeets, attendances and self registration without attendings
        :param attending: an attending object
        :return: None
        """
        for attendingmeet in attending.attendingmeet_set.filter(is_removed=False):
            Attendance.objects.filter(
                gathering__meet=attendingmeet.meet,
                attending=attendingmeet.attending,
                is_removed=False,
            ).delete()
        attending.attendingmeet_set.filter(is_removed=False).delete()
        registration = attending.registration
        attending.registration = None
        if (
            registration
            and registration.registrant == attending.attendee
            and not registration.attending_set.filter(is_removed=False).exclude(pk=attending.pk)
        ):
            registration.delete()
        attending.delete()

    # @staticmethod
    # def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, orderbys):
    #     orderby_list = AttendingService.orderby_parser(orderbys)
    #     filters = Q(
    #         meets__assembly__division__organization=current_user.organization
    #     ).add(Q(meets__slug__in=meet_slugs), Q.AND).add(Q(attendingmeet__character__slug__in=character_slugs), Q.AND)
    #     # Todo 20220512 let scheduler see other attenings too?
    #     if not current_user.can_see_all_organizational_meets_attendees():
    #         filters.add(Q(attendee=current_user.attendee), Q.AND)
    #
    #     if start:
    #         filters.add((Q(attendingmeet__finish__isnull=True) | Q(attendingmeet__finish__gte=start)), Q.AND)
    #     if finish:
    #         filters.add((Q(attendingmeet__start__isnull=True) | Q(attendingmeet__start__lte=finish)), Q.AND)
    #     return Attending.objects.annotate(assembly=F("meet__assembly")).filter(filters).order_by(*orderby_list)
    #
    @staticmethod
    def get_roster_data(organization, meet_slugs, start, finish, skip, take, sort_list=None, search_value=None):
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

        gathering_list = [
            {
                "id": g.id,
                "display_name": g.display_name,
                "start": g.start.isoformat() if g.start else None,
                "meet_id": g.meet_id
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

        if search_value:
            search_filter = (
                Q(first_name__icontains=search_value) |
                Q(last_name__icontains=search_value) |
                Q(infos__names__original__icontains=search_value) |
                Q(infos__contacts__icontains=search_value) |
                Q(attendings__attendingmeet__team__display_name__icontains=search_value)
            )
            attendees_qs = attendees_qs.filter(search_filter)

        normalized_sort_list = []
        for s in sort_list:
            if s.startswith('-attendee__'):
                normalized_sort_list.append('-' + s[11:])
            elif s.startswith('attendee__'):
                normalized_sort_list.append(s[10:])
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
                    Value('character_id'), 'attendings__attendingmeet__character_id',
                    Value('start'), 'attendings__attendingmeet__start',
                    Value('finish'), 'attendings__attendingmeet__finish',
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

            rows.append({
                "attending_id": primary_attending_id,
                "attendee_id": attendee.id,
                "attendee_name": attendee.display_label,
                "photo_url": photo_url,
                "team__display_name": attendee.team__display_name,
                "attendances": attendee.attendances,
                "attendingmeets": attendee.attendingmeets,
                "total_attendances": attendee.total_attendances,
            })
            
        return gathering_list, rows, total_count
