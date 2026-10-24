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

        kid_data = request.data.get("kid_data")
        if not kid_data or not isinstance(kid_data, dict):
            raise ValidationError({"kid_data": "kid_data dictionary is required."})

        parent_data = request.data.get("parent_data")
        companions = request.data.get("companions")
        unaccompanied = bool(request.data.get("unaccompanied", False))
        gathering_id = request.data.get("gathering_id")

        result = AttendeeService.fast_onboard(
            current_user=request.user,
            meet_slug=meet_slug,
            kid_data=kid_data,
            parent_data=parent_data,
            companions=companions,
            unaccompanied=unaccompanied,
            gathering_id=gathering_id,
        )

        return Response(result, status=status.HTTP_201_CREATED)


api_fast_onboard_attendee_viewset = ApiFastOnboardAttendeeViewSet
