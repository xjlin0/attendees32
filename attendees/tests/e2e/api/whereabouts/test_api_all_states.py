"""``/whereabouts/api/all_states/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAllStates:
    def test_states_are_available_for_the_address_form(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/all_states/", {"searchValue": "Calif"})
        assert response.status_code == 200
        assert "California" in {row["name"] for row in response.json()["data"]}
