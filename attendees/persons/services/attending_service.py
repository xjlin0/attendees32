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
