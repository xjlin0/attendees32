"""``/occasions/api/series_gatherings/`` against the golden congregation."""

from datetime import timedelta

import pytest

from attendees.occasions.models import Gathering
from attendees.occasions.models import Meet
from attendees.persons.models import Utility
from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestSeriesGatherings:
    def test_a_coworker_can_batch_create_gatherings(self, golden, api_login):
        """``series_gatherings`` walks the meet's schedule rules."""
        meet = Meet.objects.get(slug=MeetSlugs.THE_ROCK)
        before = Gathering.objects.filter(meet=meet).count()
        now = Utility.now_with_timezone()
        client = api_login("golden_children_organizer")
        response = client.post(
            "/occasions/api/series_gatherings/",
            {
                "meet_slug": MeetSlugs.THE_ROCK,
                "begin": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=22)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "duration": 75,
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        payload = response.json()
        assert payload["success"] is True
        assert Gathering.objects.filter(meet=meet).count() == (
            before + payload["number_created"]
        )

    def test_batch_creation_is_refused_without_the_right_group(self, golden, api_login):
        client = api_login("golden_member")
        response = client.post(
            "/occasions/api/series_gatherings/",
            {"meet_slug": MeetSlugs.THE_ROCK, "begin": "", "end": "", "duration": 75},
            format="json",
        )
        assert "does not have permissions to visit such route" in response.content.decode()
