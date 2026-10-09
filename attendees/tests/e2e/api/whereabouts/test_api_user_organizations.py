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

    def test_a_token_authenticated_client_reads_the_grade_converter(self, golden, token_client):
        """An API client maps grades through the organization's own list."""
        response = token_client("golden_member").get("/whereabouts/api/user_organizations/")
        assert response.status_code == 200, response.content
        rows = response.json()["data"]
        assert [row["id"] for row in rows] == [ORGANIZATION_ID]
        assert rows[0]["infos"]["grade_converter"][7] == "G1"

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        assert client.get("/whereabouts/api/user_organizations/").status_code == 403

    def test_the_organization_cannot_be_written_here(self, golden, api_login):
        """A member must not be able to put their own group into the organization's
        privilege lists through this endpoint."""
        client = api_login("golden_member")
        response = client.patch(
            f"/whereabouts/api/user_organizations/{ORGANIZATION_ID}/",
            {"infos": {"counselor": ["participant"]}},
            format="json",
        )
        assert response.status_code == 405
