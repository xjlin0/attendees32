from datetime import datetime, timezone

from django.db.models import Q
from django.db.models.expressions import F

from attendees.occasions.models import Attendance
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
            and not registration.attending_set.filter(is_removed=False)
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
    # @staticmethod
    # def orderby_parser(orderbys):
    #     """
    #     generates sorter (column) based on user's choice
    #     :param orderbys: list of search params
    #     :return: a List of sorter for order_by()
    #     """
    #     orderby_list = (
    #         []
    #     )  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]
    #
    #     for orderby_dict in orderbys:
    #         field = orderby_dict.get("selector", "id").replace(".", "__")
    #         direction = "-" if orderby_dict.get("desc", False) else ""
    #         orderby_list.append(direction + field)
    #
    #     return orderby_list
