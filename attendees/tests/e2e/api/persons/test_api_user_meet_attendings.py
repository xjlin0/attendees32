"""``/persons/api/user_meet_attendings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestUserMeetAttendings:
    def test_a_user_can_list_their_own_meets_attendings(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/user_meet_attendings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE},
        )
        assert response.status_code == 200
