"""``/occasions/api/organization_meet_teams/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestOrganizationMeetTeams:
    def test_teams_are_listed_per_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_teams/",
            {"meets[]": MeetSlugs.CHINESE_CHOIR, "take": 100},
        )
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert {"女高音 soprano", "男低音 bass"} <= names
