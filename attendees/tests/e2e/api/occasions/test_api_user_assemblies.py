"""``/occasions/api/user_assemblies/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs

pytestmark = pytest.mark.django_db


class TestUserAssemblies:
    def test_assemblies_are_listed_for_the_users_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/user_assemblies/", {"take": 100})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert AssemblySlugs.CONGREGATION_DATA in slugs
        assert AssemblySlugs.CROSSING_YOUTH in slugs  # added by the golden builder
        assert "heaven_throne_worship" not in slugs  # a different organization

    def test_assemblies_can_be_searched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/user_assemblies/",
            {"searchValue": "Youth", "searchExpr": "display_name",
             "searchOperation": "contains"},
        )
        assert {row["slug"] for row in response.json()["data"]} == {
            AssemblySlugs.CROSSING_YOUTH
        }

    def test_an_account_without_an_organization_is_refused(self, golden, api_login):
        client = api_login("golden_outsider")
        assert client.get("/occasions/api/user_assemblies/").status_code == 403

    def test_a_login_without_an_organization_is_refused(self, golden, api_login):
        client = api_login("golden_outsider")
        assert client.get("/occasions/api/user_assemblies/").status_code == 403
