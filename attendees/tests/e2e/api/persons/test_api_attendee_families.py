"""``/persons/api/attendee_families/`` against the golden congregation."""

import pytest

from attendees.persons.models import Folk
from attendees.tests.golden.constants import FolkCategory
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestAttendeeFamilies:
    def test_an_attendees_families_are_listed(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 200
        assert any(
            row["display_name"].startswith("陳志明家")
            for row in response.json()["data"]
        )

    def test_a_family_can_be_created_and_joined(self, golden, api_login):
        wilson = golden.attendee("wong_wilson")
        client = target(api_login("golden_data_organizer"), wilson)
        response = client.post(
            "/persons/api/attendee_families/",
            {
                "category": FolkCategory.OTHER,
                "division": 2,
                "display_name": "Wong small group",
                "infos": {"print_directory": False},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        assert Folk.objects.filter(display_name="Wong small group").exists()

    def test_the_drf_guard_refuses_a_stranger(self, golden, api_login):
        client = api_login("golden_crossing_member")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_grace").id)
        )
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 403

    def test_the_drf_guard_lets_a_scheduler_through(self, golden, api_login):
        client = api_login("golden_member")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 200
