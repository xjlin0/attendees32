# from attendees.persons.models import Relationship


class FolkService:
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
