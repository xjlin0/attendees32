"""``/persons/api/family_organization_attendings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestFamilyOrganizationAttendings:
    def test_family_attendings_are_listed_for_a_parent(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/family_organization_attendings/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200
