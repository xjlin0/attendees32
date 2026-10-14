"""``/occasions/api/organization_calendars/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestOrganizationCalendars:
    def test_calendars_are_listed_for_the_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_calendars/", {"take": 50})
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1
