"""``/whereabouts/api/all_addresses/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAllAddresses:
    def test_the_golden_households_produced_real_addresses(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/all_addresses/", {"take": 10})
        assert response.status_code == 200
        assert response.json()["totalCount"] > 100

    def test_addresses_can_be_searched_by_street(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/all_addresses/", {"searchValue": "Tennyson"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1
