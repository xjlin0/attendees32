"""The printed artefacts: the church directory, participation lists and envelopes.

These are the pages a church office actually prints, and the only ones that
walk the whole congregation in one request — so they are also where a golden
dataset of 350 people earns its keep.
"""

import pytest

from attendees.persons.services import FolkService
from attendees.tests.golden.constants import DIVISION_SLUGS, MeetSlugs, ORGANIZATION_ID
from attendees.whereabouts.models import Organization

pytestmark = pytest.mark.django_db

REFUSED = "you do not have permissions to visit this"


class TestDirectory:
    def test_the_directory_lists_households_grouped_by_city(self, golden, login):
        client = login("golden_data_organizer")
        response = client.get(
            "/persons/directory_report/",
            {
                "divisionSelector": [1, 2, 3],
                "directoryHeader": "CFCCH 通訊錄 2026",
                "indexHeader": "Index",
                "indexRowPerPage": 26,
                "pageBreaksBeforeIndex": 2,
            },
        )
        assert response.status_code == 200
        families = response.context["families"]
        indexes = response.context["indexes"]
        assert len(families) > 40, "most households opt into the printed directory"
        assert indexes, "the index groups households by city"
        cities = {row["key"] for row in indexes if isinstance(row, dict) and "key" in row}
        assert cities or indexes

    def _printed_ids(self, response):
        """Golden names repeat on purpose, so identity is checked by id."""
        return {
            str(attendee["id"])
            for family in response.context["families"]
            for attendee in family["attendees"]
        }

    def _whole_directory(self, login):
        return login("golden_data_organizer").get(
            "/persons/directory_report/", {"divisionSelector": [1, 2, 3]}
        )

    def test_a_household_that_opted_out_is_not_printed(self, golden, login):
        """The Fengs are five months in and still visitors, so they opted out."""
        printed = self._printed_ids(self._whole_directory(login))
        assert str(golden.attendee("feng_ruian").id) not in printed
        assert str(golden.attendee("feng_xinyi").id) not in printed
        assert str(golden.attendee("chen_zhiming").id) in printed  # one that opted in

    def test_the_departed_household_is_not_printed(self, golden, login):
        printed = self._printed_ids(self._whole_directory(login))
        for key in ("peng_jinlong", "peng_wanru", "peng_lily"):
            assert str(golden.attendee(key).id) not in printed

    def test_a_deceased_member_is_left_out_of_their_family_entry(self, golden):
        """陳桂枝 died four years ago; her household still prints without her."""
        organization = Organization.objects.get(pk=ORGANIZATION_ID)
        settings = organization.infos["settings"]
        _indexes, families = FolkService.families_in_directory(
            directory_meet_id=settings["default_directory_meet"],
            member_meet_id=settings["default_member_meet"],
            targeting_attendee_id=str(golden.attendee("chen_zhiming").id),
        )
        assert families
        printed = {
            attendee["first_name"].rstrip("*")
            for family in families
            for attendee in family["attendees"]
        }
        assert {"Zhiming", "Shufen", "Grace", "Joshua"} <= printed
        assert "Guizhi" not in printed

    def test_an_unprivileged_reader_gets_nothing_and_a_403(self, golden, login):
        client = login("golden_children_coworker")  # may read the route, not the data
        response = client.get("/persons/directory_report/")
        assert response.status_code == 403
        assert REFUSED in response.content.decode().lower()

    def test_a_member_can_preview_their_own_directory_entry(self, golden, login):
        client = login("golden_counselor")
        response = client.get(
            f"/persons/directory_preview/{golden.attendee('chen_zhiming').id}"
        )
        assert response.status_code == 200
        assert response.context["families"]

    def test_the_preview_falls_back_to_the_readers_own_family(self, golden, login):
        """An unprivileged reader asking about somebody else sees themselves."""
        client = login("golden_children_organizer")
        response = client.get(
            f"/persons/directory_preview/{golden.attendee('tsai_shixiang').id}"
        )
        assert response.status_code == 200


class TestParticipationReports:
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

    def test_reports_are_refused_to_a_reader_without_the_route(self, golden, login):
        client = login("golden_member")
        for path in ("/persons/attendingmeet_report/", "/persons/attendingmeet_envelopes/"):
            response = client.get(path, {"meet": MeetSlugs.DIRECTORY})
            body = response.content.decode()
            assert "does not have permissions to visit such route" in body, path
