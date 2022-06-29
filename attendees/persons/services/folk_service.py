from django.db.models import OuterRef, Subquery
from django.db.models.functions import Concat

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, Folk, Utility


class FolkService:
    @staticmethod
    def families_in_directory():
        directory_meet = Meet.objects.get(pk=8)
        attendee_subquery = Attendee.objects.filter(folks=OuterRef('pk'))  # implicitly ordered at FolkAttendee model
        return Folk.objects.annotate(
            householder_name=Concat(
                Subquery(attendee_subquery.values_list('last_name')[:1]),
                Subquery(attendee_subquery.values_list('first_name')[:1]),
            )
        ).filter(
            category=0,  # Family
            is_removed=False,
            infos__print_directory=True,
            attendees__in=Attendee.objects.filter(
                attendings__in=directory_meet.attendings.filter(
                    attendingmeet__finish__gte=Utility.now_with_timezone()
                ),
                deathday=None,
                is_removed=False,
            ),
        ).distinct().order_by('householder_name')

    @staticmethod
    def destroy_with_associations(folk, attendee):
        """
        No permission check.
        if family have more than one FamilyAttendees:
            only delete the FamilyAttendees, and reset non-blood Relationships. Places and Family still remained
        if family have only one FamilyAttendees (regardless which FamilyAttendees):
            delete family, places, FamilyAttendees and reset non-blood Relationships

        :param folk: a folk object
        :param attendee: an attendee object, whose name will be removed from family display_name
        :return: None
        """

        if (
            folk.folkattendee_set.count() < 2
            and folk.folkattendee_set.first() == attendee
        ):
            # Relationship.objects.filter(in_family=folk.id, relation__consanguinity=False, is_removed=False).delete()
            # Relationship.objects.filter(in_family=folk.id, relation__consanguinity=True, is_removed=False).update(in_family=None)
            folk.places.filter(is_removed=False).delete()
            folk.folkattendee_set.filter(is_removed=False).delete()
            folk.delete()

        else:
            family_name = folk.display_name
            for attendee_name in attendee.all_names():
                if attendee_name is not None:
                    family_name.replace(attendee_name, "")
            folk.display_name = family_name
            folk.save()
            # Relationship.objects.filter(from_attendee=attendee, in_family=folk.id, relation__consanguinity=False, is_removed=False).delete()
            folk.folkattendee_set.filter(attendee=attendee, is_removed=False).delete()
