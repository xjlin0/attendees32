"""``/occasions/api/organization_characters/`` against the golden congregation."""

import pytest

from attendees.tests.e2e.helpers import JUNIOR_STUDENT_SLUG

pytestmark = pytest.mark.django_db


class TestOrganizationCharacters:
    def test_characters_are_listed_for_the_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_characters/", {"take": 200})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert JUNIOR_STUDENT_SLUG in slugs
        assert "golden_youth_student" in slugs
