"""``/whereabouts/api/user_places/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestUserPlaces:
    def test_places_are_searchable_by_a_privileged_user(self, golden, api_login):
        """``user_places`` only serves privileged logins; the ordinary-member
        branch reaches for an attribute Attendee does not have."""
        client = api_login("golden_data_organizer")
        response = client.get(
            "/whereabouts/api/user_places/", {"searchValue": "Tennyson"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1
