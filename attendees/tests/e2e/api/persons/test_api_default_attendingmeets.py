"""``/persons/api/default_attendingmeets/`` against the golden congregation."""

import pytest

from attendees.occasions.models import Meet
from attendees.persons.models import AttendingMeet
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestDefaultAttendingmeets:
    def test_joining_a_meet_through_the_default_endpoint(self, golden, api_login):
        library = Meet.objects.get(slug=MeetSlugs.LIBRARY)
        wilson = golden.attendee("wong_wilson")
        assert not AttendingMeet.objects.filter(
            meet=library, attending__attendee=wilson
        ).exists()
        client = target(api_login("golden_data_organizer"), wilson)
        response = client.put(
            "/persons/api/default_attendingmeets/",
            {"action": "join", "meet": MeetSlugs.LIBRARY},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert AttendingMeet.objects.filter(
            meet=library, attending__attendee=wilson
        ).exists()

    def test_leaving_a_meet_ends_the_participation(self, golden, api_login):
        from attendees.persons.models import Utility

        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.put(
            "/persons/api/default_attendingmeets/",
            {"action": "leave", "meet": MeetSlugs.DIRECTORY},
            format="json",
        )
        assert response.status_code == 200, response.content
        participation = AttendingMeet.objects.filter(
            meet__slug=MeetSlugs.DIRECTORY, attending__attendee=zhiming
        ).order_by("created").last()
        assert participation.finish <= Utility.now_with_timezone()

    def test_the_spy_guard_holds_for_a_token_client(self, golden, token_client):
        """A token client is held to the same rules as a session: an ordinary
        member may not reach a stranger's record, and a deleted attendee is a 404."""
        stranger = target(token_client("golden_crossing_member"), golden.attendee("chen_grace"))
        assert stranger.put("/persons/api/default_attendingmeets/", {"action": "join", "meet": MeetSlugs.LIBRARY}, format="json").status_code == 403

        deleted = target(token_client("golden_data_organizer"), golden.attendee("peng_jinlong"))
        assert deleted.put("/persons/api/default_attendingmeets/", {"action": "join", "meet": MeetSlugs.LIBRARY}, format="json").status_code == 404

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.put(
            "/persons/api/default_attendingmeets/",
            {"action": "join", "meet": MeetSlugs.LIBRARY},
            content_type="application/json",
        )
        assert response.status_code == 403
