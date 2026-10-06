"""``/occasions/api/family_organization_gatherings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestFamilyOrganizationGatherings:
    def test_a_family_sees_the_gatherings_of_the_meets_they_joined(
        self, golden, api_login
    ):
        client = api_login("golden_member")
        response = client.get(
            "/occasions/api/family_organization_gatherings/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200
