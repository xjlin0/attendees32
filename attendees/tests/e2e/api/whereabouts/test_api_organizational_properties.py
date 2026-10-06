"""``/whereabouts/api/organizational_properties/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestOrganizationalProperties:
    def test_the_organizations_properties_are_listed(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/organizational_properties/", {"take": 100})
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert "CFCCH Fellowship Hall" in names
