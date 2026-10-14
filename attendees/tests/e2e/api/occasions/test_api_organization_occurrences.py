"""``/occasions/api/organization_occurrences/`` against the golden congregation."""

from datetime import timedelta

import pytest

from attendees.persons.models import Utility

pytestmark = pytest.mark.django_db


class TestOrganizationOccurrences:
    def test_occurrences_need_a_window(self, golden, api_login):
        client = api_login("golden_data_organizer")
        now = Utility.now_with_timezone()
        response = client.get(
            "/occasions/api/organization_occurrences/",
            {
                "start": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "take": 50,
            },
        )
        assert response.status_code == 200
