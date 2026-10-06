"""``/occasions/api/series_attendances/`` against the golden congregation."""

from datetime import timedelta

import pytest

from attendees.persons.models import Utility
from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestSeriesAttendances:
    def test_batch_creating_attendances_follows_the_gatherings(self, golden, api_login):
        now = Utility.now_with_timezone()
        client = api_login("golden_children_organizer")
        response = client.post(
            "/occasions/api/series_attendances/",
            {
                "meet_slug": MeetSlugs.THE_ROCK,
                "begin": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "duration": 75,
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["gathering_generation_success"] is True
