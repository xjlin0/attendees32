"""``/persons/api/all_categories/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAllCategories:
    def test_categories_can_be_filtered_by_type(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/persons/api/all_categories/", {"type": "folk"})
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert {"Family", "Other", "Carpool"} <= names
