"""The attendingmeet_envelopes page against the golden congregation."""

import pytest

from attendees.tests.golden.constants import DIVISION_SLUGS
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import ROUTE_REFUSED

pytestmark = pytest.mark.django_db


class TestAttendingmeetEnvelopes:
    def test_envelopes_carry_one_address_per_household(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get(
            "/persons/attendingmeet_envelopes/",
            {
                "meet": MeetSlugs.DIRECTORY,
                "divisions": [DIVISION_SLUGS[1], DIVISION_SLUGS[2]],
                "reportTitle": "CFCCH",
                "senderColor": "#112233",
                "newLines": 3,
            },
        )
        assert response.status_code == 200
        assert response.context["families"]
        assert response.context["sender_color"] == "#112233"
        assert list(response.context["newLines"]) == [0, 1, 2]

    def test_a_reader_without_the_route_is_refused(self, golden, login):
        response = login("golden_member").get("/persons/attendingmeet_envelopes/", {"meet": MeetSlugs.DIRECTORY})
        assert ROUTE_REFUSED in response.content.decode()

    def test_a_data_admin_gets_the_data(self, golden, login):
        response = login("golden_data_organizer").get("/persons/attendingmeet_envelopes/?meet=d7c8Fd_cfcch_congregation_directory")
        assert response.status_code == 200
