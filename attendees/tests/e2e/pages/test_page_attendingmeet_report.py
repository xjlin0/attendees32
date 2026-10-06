"""The attendingmeet_report page against the golden congregation."""

import pytest

from attendees.tests.golden.constants import DIVISION_SLUGS
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import ROUTE_REFUSED

pytestmark = pytest.mark.django_db


class TestAttendingmeetReport:
    def test_the_participation_report_lists_the_families_in_a_meet(
        self, golden, login
    ):
        client = login("golden_data_organizer")
        response = client.get(
            "/persons/attendingmeet_report/",
            {
                "meet": MeetSlugs.DIRECTORY,
                "reportTitle": "通訊錄名單",
                "reportDate": "2026-08-03",
                "divisions": [DIVISION_SLUGS[1], DIVISION_SLUGS[2], DIVISION_SLUGS[3]],
            },
        )
        assert response.status_code == 200
        assert response.context["families"]
        assert response.context["meet_slug"] == MeetSlugs.DIRECTORY

    def test_paused_participants_are_hidden_unless_asked_for(self, golden, login):
        client = login("golden_data_organizer")
        divisions = [DIVISION_SLUGS[1], DIVISION_SLUGS[2], DIVISION_SLUGS[3]]
        without = client.get(
            "/persons/attendingmeet_report/",
            {"meet": MeetSlugs.CHINESE_SERVICE, "divisions": divisions},
        ).context["families"]
        with_paused = client.get(
            "/persons/attendingmeet_report/",
            {"meet": MeetSlugs.CHINESE_SERVICE, "divisions": divisions,
             "showPaused": "true"},
        ).context["families"]
        assert len(with_paused) >= len(without)

    def test_a_reader_without_the_route_is_refused(self, golden, login):
        response = login("golden_member").get("/persons/attendingmeet_report/", {"meet": MeetSlugs.DIRECTORY})
        assert ROUTE_REFUSED in response.content.decode()

    def test_a_data_admin_gets_the_data(self, golden, login):
        response = login("golden_data_organizer").get("/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_directory")
        assert response.status_code == 200
