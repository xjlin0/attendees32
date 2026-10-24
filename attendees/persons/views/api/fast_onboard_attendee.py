from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from attendees.persons.services import AttendeeService


class ApiFastOnboardAttendeeViewSet(viewsets.ViewSet):
    """
    API endpoint to quickly onboard and enroll a new attendee into a meet.
    Supports atomic creation of kid attendee, optional parent attendee,
    family folk association, and gathering attendance check-in.
    """

    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        meet_slug = request.data.get("meet_slug")
        if not meet_slug:
            raise ValidationError({"meet_slug": "meet_slug is required."})

        attendees_data = request.data.get("attendees_data")
        if not attendees_data:
            kid_data = request.data.get("kid_data")
            if kid_data and isinstance(kid_data, dict):
                attendees_data = [kid_data]
            elif isinstance(kid_data, list):
                attendees_data = kid_data

        if not attendees_data or not isinstance(attendees_data, list):
            raise ValidationError({"attendees_data": "attendees_data list is required."})

        companions = request.data.get("companions")
        if not companions and request.data.get("parent_data"):
            p_data = request.data.get("parent_data")
            companions = [p_data] if isinstance(p_data, dict) else p_data

        unaccompanied = bool(request.data.get("unaccompanied", False))
        gathering_id = request.data.get("gathering_id")

        result = AttendeeService.fast_onboard(
            current_user=request.user,
            meet_slug=meet_slug,
            attendees_data=attendees_data,
            companions=companions,
            unaccompanied=unaccompanied,
            gathering_id=gathering_id,
        )

        return Response(result, status=status.HTTP_201_CREATED)


api_fast_onboard_attendee_viewset = ApiFastOnboardAttendeeViewSet
