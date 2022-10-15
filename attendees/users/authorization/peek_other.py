from attendees.persons.models import Attendee


class PeekOther:
    @staticmethod
    def get_attendee_or_self(current_user, attendee_id):
        attendee = current_user.attendee if hasattr(current_user, 'attendee') else None
        if (
            attendee_id is not None and current_user.privileged
        ):  # data_admins or counselor group
            other_user = Attendee.objects.filter(pk=attendee_id).first()
            if other_user is not None:
                attendee = other_user
        return attendee
