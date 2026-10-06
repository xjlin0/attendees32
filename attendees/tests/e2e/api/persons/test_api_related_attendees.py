"""``/persons/api/related_attendees/`` against the golden congregation."""

import pytest

from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestRelatedAttendees:
    def test_related_attendees_are_reachable(self, golden, api_login):
        joshua = golden.attendee("chen_joshua")
        client = target(api_login("golden_member"), joshua)
        response = client.get("/persons/api/related_attendees/")
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_a_member_cannot_browse_a_stranger_relations(self, golden, api_login):
        stranger = golden.attendee("wong_wilson")
        client = target(api_login("golden_member"), stranger)
        response = client.get("/persons/api/related_attendees/")
        assert response.status_code == 403
