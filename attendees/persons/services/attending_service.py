from datetime import datetime, timezone

from django.db.models import Q, Value, Count, Func, JSONField
from django.db.models.expressions import F
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import JSONBAgg

from attendees.occasions.models import Attendance, Gathering
from attendees.persons.models import Attending


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
    def get_roster_data(organization, meet_slugs, start, finish, skip, take, sort_list=None):
        if not sort_list:
            sort_list = ['attendee__first_name', 'attendee__last_name']
            
        # 1. Query Gatherings (Columns)
        gatherings = Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization=organization,
            start__gte=start,
            finish__lte=finish,
            is_removed=False
        ).order_by('start')

        gathering_list = [
            {
                "id": g.id,
                "display_name": g.display_name,
                "start": g.start.isoformat() if g.start else None,
                "meet_id": g.meet_id
            }
            for g in gatherings
        ]

        # 2. Query Attendings (Rows) with Database Aggregation
        attendings_qs = Attending.objects.filter(
            meets__slug__in=meet_slugs,
            is_removed=False
        ).annotate(
            total_attendances=Count(
                'attendance',
                filter=Q(
                    attendance__gathering__in=gatherings,
                    attendance__is_removed=False
                ) & ~Q(attendance__category_id=1),
                distinct=True
            ),
            attendances=Coalesce(JSONBAgg(
                Func(
                    Value('attendance_id'), 'attendance__id',
                    Value('category_id'), 'attendance__category__id',
                    Value('category_name'), 'attendance__category__display_name',
                    Value('gathering_id'), 'attendance__gathering__id',
                    Value('start'), 'attendance__start',
                    Value('finish'), 'attendance__finish',
                    function='jsonb_build_object',
                ),
                filter=Q(attendance__gathering__in=gatherings, attendance__is_removed=False),
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
            attendingmeets=Coalesce(JSONBAgg(
                Func(
                    Value('meet_id'), 'attendingmeet__meet_id',
                    Value('start'), 'attendingmeet__start',
                    Value('finish'), 'attendingmeet__finish',
                    function='jsonb_build_object',
                ),
                filter=Q(attendingmeet__meet__slug__in=meet_slugs, attendingmeet__is_removed=False),
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
        ).select_related('attendee').distinct().order_by(*sort_list)

        total_count = attendings_qs.count()
        attendings_page = attendings_qs[skip: skip + take]

        # 3. Build Response
        rows = []
        for attending in attendings_page:
            photo_url = None
            if attending.attendee.photo:
                try:
                    photo_url = attending.attendee.photo.url
                except ValueError:
                    pass

            rows.append({
                "attending_id": attending.id,
                "attendee_id": attending.attendee.id,
                "attendee_name": attending.attendee.display_label,
                "photo_url": photo_url,
                "attendances": attending.attendances,
                "attendingmeets": attending.attendingmeets,
                "total_attendances": attending.total_attendances,
            })
            
        return gathering_list, rows, total_count
