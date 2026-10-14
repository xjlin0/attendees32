"""The attendee_update_self page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendeeUpdateSelf:
    def test_the_self_page_targets_the_signed_in_attendee(self, golden, login):
        client = login("golden_member")
        response = client.get("/persons/attendee/self")
        assert response.status_code == 200
        assert response.context["targeting_attendee_id"] == str(
            golden.attendee("chen_zhiming").id
        )
        assert response.context["grade_converter"][7] == "G1"
