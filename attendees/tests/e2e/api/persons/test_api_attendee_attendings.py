"""``/persons/api/attendee_attendings/`` against the golden congregation."""

import pytest

from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestAttendeeAttendings:
    def test_attendings_for_an_attendee_are_listed(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.get("/persons/api/attendee_attendings/")
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = target(token_client("golden_data_organizer"), golden.attendee("chen_zhiming"))
        response = client.get("/persons/api/attendee_attendings/")
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/attendee_attendings/")
        assert response.status_code == 403
