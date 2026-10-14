"""``/whereabouts/api/organizational_rooms/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestOrganizationalRooms:
    def test_the_organizations_rooms_are_listed(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/organizational_rooms/", {"take": 100})
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert "CFCCH Zoom 3583017026" in names

    def test_rooms_can_be_searched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/organizational_rooms/", {"searchValue": "Zoom"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1
