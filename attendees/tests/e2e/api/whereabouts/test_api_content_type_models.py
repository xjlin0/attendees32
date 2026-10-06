"""``/whereabouts/api/content_type_models/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestContentTypeModels:
    def test_location_content_types_are_listed_for_the_site_picker(
        self, golden, api_login
    ):
        """The extra ``genres``/``display_order`` columns, filled in by
        ``manage.py update_content_types`` and read back by raw SQL."""
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/content_type_models/", {"query": "location"}
        )
        assert response.status_code == 200
        models = {row["model"] for row in response.json()["data"]}
        assert {"room", "suite", "property", "campus"} <= models
