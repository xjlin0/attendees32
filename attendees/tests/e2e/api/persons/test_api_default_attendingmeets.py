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
