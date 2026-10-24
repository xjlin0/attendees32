import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from attendees.persons.services import AttendeeService

logger = logging.getLogger(__name__)


class ApiSearchAttendeesForRosterViewSet(viewsets.ViewSet):
    """
    API endpoint to search attendees for quick addition / enrollment into a roster.
    Requires query parameter 'meet_slug'.
    Optional query parameter 'q' (search keyword: name, phone, email, etc.).
    """

    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            messages = exc.messages if hasattr(exc, "messages") else [str(exc)]
            return Response(
                {"detail": " ".join(messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return super().handle_exception(exc)
        except Exception as unhandled_exc:
            logger.exception(f"Unhandled exception in {self.__class__.__name__}: {unhandled_exc}")
            return Response(
                {
                    "detail": f"Internal server error: {str(unhandled_exc)}",
                    "error": str(unhandled_exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
