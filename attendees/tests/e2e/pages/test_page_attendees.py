"""The attendees page against the golden congregation."""

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestAttendees:
    def test_the_roster_page_lists_the_meets_the_user_may_see(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get("/persons/attendees/")
        assert response.status_code == 200
        meets = response.context["available_meets_json"]
        slugs = {meet["slug"] for meet in meets}
        assert MeetSlugs.CHINESE_SERVICE in slugs
        assert MeetSlugs.ENGLISH_SERVICE in slugs
        assert response.context["allowed_to_create_attendee"] is True

    def test_an_ordinary_member_sees_fewer_meets_than_a_data_admin(self, golden, login):
        member = login("golden_member").get("/persons/attendees/")
        member_slugs = {m["slug"] for m in member.context["available_meets_json"]}
        assert member.context["allowed_to_create_attendee"] is False
        assert MeetSlugs.DIRECTORY not in member_slugs  # shown_audience=False

        client = login("golden_data_organizer")
        admin = client.get("/persons/attendees/")
        admin_slugs = {m["slug"] for m in admin.context["available_meets_json"]}
        assert MeetSlugs.DIRECTORY in admin_slugs
        assert member_slugs < admin_slugs
