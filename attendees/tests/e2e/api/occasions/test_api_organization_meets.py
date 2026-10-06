"""``/occasions/api/organization_meets/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestOrganizationMeets:
    def test_meets_are_listed_by_slug(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_meets/", {"take": 100})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {MeetSlugs.CHINESE_SERVICE, MeetSlugs.ENGLISH_SERVICE,
                MeetSlugs.THE_ROCK} <= slugs
