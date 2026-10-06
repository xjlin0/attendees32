"""``/persons/api/organization_meet_character_attendingmeets/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

from attendees.tests.e2e.helpers import JUNIOR_STUDENT_SLUG

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

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = token_client("golden_data_organizer")
        response = client.get("/persons/api/organization_meet_character_attendingmeets/", {"meets[]": MeetSlugs.THE_ROCK, "characters[]": JUNIOR_STUDENT_SLUG})
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/organization_meet_character_attendingmeets/", {"meets[]": MeetSlugs.THE_ROCK, "characters[]": JUNIOR_STUDENT_SLUG})
        assert response.status_code == 403
