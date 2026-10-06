"""``/whereabouts/api/user_organizations/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import ORGANIZATION_ID

pytestmark = pytest.mark.django_db


class TestUserOrganizations:
    def test_the_users_organization_is_returned(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/whereabouts/api/user_organizations/")
        assert response.status_code == 200
        rows = response.json()["data"]
        assert [row["id"] for row in rows] == [ORGANIZATION_ID]
        assert rows[0]["infos"]["acronym"] == "CFCCH"
