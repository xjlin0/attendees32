"""The attendingmeets page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendingmeets:
    def test_the_attendingmeets_page_carries_the_grade_vocabulary(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get("/persons/attendingmeets/")
        assert response.status_code == 200
        assert response.context["user_can_write"] is True
        assert "G12" in response.context["grade_converter"]

    def test_the_attendingmeets_page_offers_merge_to_those_who_see_everyone(self, golden, login):
        client = login("golden_data_organizer")
        assert client.get("/persons/attendingmeets/").context["can_merge"] is True
