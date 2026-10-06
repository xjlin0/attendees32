"""``/whereabouts/api/user_divisions/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import DIVISION_SLUGS

pytestmark = pytest.mark.django_db


class TestUserDivisions:
    def test_all_four_divisions_are_listed(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/user_divisions/", {"take": 50})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {
            DIVISION_SLUGS[1], DIVISION_SLUGS[2], DIVISION_SLUGS[3], DIVISION_SLUGS[5]
        } <= slugs

    def test_a_single_division_can_be_fetched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/whereabouts/api/user_divisions/", {"division_id": 3})
        assert response.status_code == 200
        assert [row["slug"] for row in response.json()["data"]] == [DIVISION_SLUGS[3]]
