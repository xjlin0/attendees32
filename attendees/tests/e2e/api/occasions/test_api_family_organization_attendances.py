"""``/occasions/api/family_organization_attendances/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import window

pytestmark = pytest.mark.django_db


class TestFamilyOrganizationAttendances:
    def test_a_parent_sees_only_their_family_attendances(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/occasions/api/family_organization_attendances/",
            {
                "meets[]": MeetSlugs.THE_ROCK,
                "attendee": str(golden.attendee("chen_joshua").id),
                **window(),
            },
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert rows, "Joshua has eight weeks of The Rock history"
