"""``/persons/api/organization_meet_character_attendings_for_attendingmeet/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestOrganizationMeetCharacterAttendingsForAttendingmeet:
    def test_attendings_can_be_searched_by_attendee(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/organization_meet_character_attendings_for_attendingmeet/",
            {"searchValue": "Grace", "searchExpr": "attendee", "searchOperation": "contains"},
        )
        assert response.status_code == 200
