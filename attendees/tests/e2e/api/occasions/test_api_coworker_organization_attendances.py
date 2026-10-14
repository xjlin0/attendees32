"""``/occasions/api/coworker_organization_attendances/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import window

pytestmark = pytest.mark.django_db


class TestCoworkerOrganizationAttendances:
    def test_a_coworker_sees_the_organizations_attendances(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            "/occasions/api/coworker_organization_attendances/",
            {"meets[]": MeetSlugs.THE_ROCK, **window(), "take": 10},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 0
