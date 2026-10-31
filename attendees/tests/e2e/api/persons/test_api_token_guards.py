"""Endpoints a token-authenticated client could not reach, against the golden congregation.

``LoginRequiredMixin`` and ``SpyGuard`` run in ``dispatch()`` before DRF
authenticates, so a request carrying a valid ``Authorization: Token`` header was
still anonymous when they looked: one endpoint redirected it to the login page,
another refused it as a user without an attendee. As DRF permissions they see
the authenticated user, and session users keep the same rules.
"""

import pytest

from attendees.tests.golden.builder import GOLDEN_MEET_IDS, GOLDEN_MEET_SLUGS

pytestmark = pytest.mark.django_db

YOUTH_GROUP = GOLDEN_MEET_SLUGS["youth_group"]


class TestAttendingsForAttendingMeet:
    PATH = "/persons/api/organization_meet_character_attendings_for_attendingmeet/"

    def test_a_token_is_answered_not_redirected(self, golden, token_client):
        response = token_client("golden_data_organizer").get(self.PATH, {"meets[]": YOUTH_GROUP})
        assert response.status_code == 200
        assert response.json()["totalCount"] > 0

    def test_a_session_still_gets_in(self, golden, api_login):
        response = api_login("golden_data_organizer").get(self.PATH, {"meets[]": YOUTH_GROUP})
        assert response.status_code == 200

    def test_anonymous_is_refused_as_json(self, golden, anonymous_client):
        response = anonymous_client.get(self.PATH)
        assert response.status_code == 403
        assert "detail" in response.json()


class TestAttendingsForAttendance:
    PATH = "/persons/api/organization_meet_character_attendings_for_attendance/"

    def test_a_token_is_answered_not_redirected(self, golden, token_client):
        response = token_client("golden_data_organizer").get(self.PATH, {"meets[]": YOUTH_GROUP})
        assert response.status_code == 200
        assert response.json()["totalCount"] > 0

    def test_anonymous_is_refused_as_json(self, golden, anonymous_client):
        response = anonymous_client.get(self.PATH)
        assert response.status_code == 403
        assert "detail" in response.json()


class TestDatagridDataAttendingMeet:
    PATH = "/persons/api/datagrid_data_attendingmeet/"

    def test_a_token_sees_a_members_attendingmeets(self, golden, token_client):
        client = token_client("golden_data_organizer")
        target = golden.attendee("liu_hannah")
        response = client.get(self.PATH, HTTP_X_TARGET_ATTENDEE_ID=str(target.id))
        assert response.status_code == 200
        meets = {row["meet"] for row in response.json()["data"]}
        assert GOLDEN_MEET_IDS["youth_group"] in meets

    def test_a_token_still_cannot_spy_on_another_member(self, golden, token_client):
        client = token_client("golden_member")
        target = golden.attendee("liu_hannah")
        response = client.get(self.PATH, HTTP_X_TARGET_ATTENDEE_ID=str(target.id))
        assert response.status_code == 403

    def test_a_session_still_gets_in(self, golden, api_login):
        client = api_login("golden_data_organizer")
        target = golden.attendee("liu_hannah")
        response = client.get(self.PATH, HTTP_X_TARGET_ATTENDEE_ID=str(target.id))
        assert response.status_code == 200
