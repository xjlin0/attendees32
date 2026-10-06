"""``/persons/api/organization_meet_character_attendingmeets/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestOrganizationMeetCharacterAttendingmeets:
    def test_participations_can_be_queried_by_meet_and_character(
        self, golden, api_login
    ):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/organization_meet_character_attendingmeets/",
            {"meets[]": MeetSlugs.THE_ROCK, "characters[]": "d7c8Fd_cfcch_kid_student"},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 10
