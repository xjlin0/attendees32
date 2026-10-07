"""``/persons/api/all_relations/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import FolkCategory

pytestmark = pytest.mark.django_db


class TestAllRelations:
    def test_relations_hide_the_internal_hidden_role(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/all_relations/",
            {"category_id": FolkCategory.FAMILY, "take": 100},
        )
        assert response.status_code == 200
        titles = {row["title"] for row in response.json()["data"]}
        assert "hidden" not in titles
        assert {"father", "mother", "son", "daughter", "ward"} <= titles

    def test_a_non_counselor_only_sees_the_driver_relation_outside_families(
        self, golden, api_login
    ):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/all_relations/", {"category_id": FolkCategory.OTHER}
        )
        assert {row["title"] for row in response.json()["data"]} == {"driver"}

    def test_a_counselor_sees_every_relation(self, golden, api_login):
        client = api_login("golden_counselor")
        response = client.get(
            "/persons/api/all_relations/",
            {"category_id": FolkCategory.OTHER, "take": 100},
        )
        titles = {row["title"] for row in response.json()["data"]}
        assert {"guardian", "caregiver", "ex spouse", "neighbor"} <= titles

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = token_client("golden_data_organizer")
        response = client.get("/persons/api/all_relations/", {"category_id": FolkCategory.FAMILY, "take": 100})
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/all_relations/", {"category_id": FolkCategory.FAMILY, "take": 100})
        assert response.status_code == 403
