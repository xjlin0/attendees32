"""``/occasions/api/organization_team_gatherings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import window

pytestmark = pytest.mark.django_db


class TestOrganizationTeamGatherings:
    def test_gatherings_are_listed_for_a_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_team_gatherings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE, **window(), "take": 50},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] == 8  # eight Sundays of history
