"""The attendee_create page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendeeCreate:
    def test_the_create_page_is_offered_to_coworkers(self, golden, login):
        client = login("golden_children_organizer")
        response = client.get("/persons/attendee/new")
        assert response.status_code == 200
        assert response.context["targeting_attendee_id"] == "new"
