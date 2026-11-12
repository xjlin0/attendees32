from unittest.mock import MagicMock, patch
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APIRequestFactory

from attendees.occasions.views.api.organization_meet_character_attendances import (
    ApiOrganizationMeetCharacterAttendancesViewSet,
)


class TestApiOrganizationMeetCharacterAttendancesViewSet:
    def test_unhandled_exception_returns_500_json_not_html(self):
        factory = APIRequestFactory()
        request = factory.post("/occasions/api/organization_meet_character_attendances/", {}, format="json")
        view = ApiOrganizationMeetCharacterAttendancesViewSet()
        view.request = request

        exc = ValueError("Field 'id' expected a number but got 'start_2026-10-25T10:00:00-07:00'.")
        response = view.handle_exception(exc)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data.get("detail") == "Internal server error: Field 'id' expected a number but got 'start_2026-10-25T10:00:00-07:00'."
        assert response.data.get("error") == "Field 'id' expected a number but got 'start_2026-10-25T10:00:00-07:00'."

    def test_django_validation_error_returns_400_json_not_html(self):
        factory = APIRequestFactory()
        request = factory.post("/occasions/api/organization_meet_character_attendances/", {}, format="json")
        view = ApiOrganizationMeetCharacterAttendancesViewSet()
        view.request = request

        exc = DjangoValidationError("Invalid attendance parameters.")
        response = view.handle_exception(exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid attendance parameters." in response.data.get("detail", "")

    def test_drf_validation_error_returns_400_json_not_html(self):
        from rest_framework.exceptions import ValidationError
        factory = APIRequestFactory()
        request = factory.post("/occasions/api/organization_meet_character_attendances/", {}, format="json")
        view = ApiOrganizationMeetCharacterAttendancesViewSet()
        view.request = request

        exc = ValidationError({"gathering": "Expected an integer ID or null, but got 'start_2026-10-25T10:00:00-07:00'."})
        response = view.handle_exception(exc)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Expected an integer ID or null" in str(response.data.get("detail", ""))

