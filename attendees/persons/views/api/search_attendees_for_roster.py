from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from attendees.persons.services import AttendeeService


class ApiSearchAttendeesForRosterViewSet(viewsets.ViewSet):
    """
    API endpoint to search attendees for quick addition / enrollment into a roster.
    Requires query parameter 'meet_slug'.
    Optional query parameter 'q' (search keyword: name, phone, email, etc.).
    """

    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        meet_slug = request.query_params.get("meet_slug")
        if not meet_slug:
            raise ValidationError({"detail": "meet_slug query parameter is required."})

        query = request.query_params.get("q", "")
        results = AttendeeService.search_for_roster(
            current_user=request.user,
            meet_slug=meet_slug,
            query=query,
        )
        return Response(results, status=status.HTTP_200_OK)


api_search_attendees_for_roster_viewset = ApiSearchAttendeesForRosterViewSet
