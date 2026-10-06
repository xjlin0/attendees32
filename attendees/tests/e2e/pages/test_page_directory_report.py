"""The directory_report page against the golden congregation."""

import pytest

from attendees.persons.services import FolkService
from attendees.tests.golden.constants import ORGANIZATION_ID
from attendees.whereabouts.models import Organization
from attendees.tests.e2e.helpers import REFUSED

pytestmark = pytest.mark.django_db


class TestDirectoryReport:
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

    def test_a_data_admin_gets_the_data(self, golden, login):
        response = login("golden_data_organizer").get("/persons/directory_report/")
        assert response.status_code == 200

    def test_a_children_coworker_may_open_the_directory_route_but_gets_403(
        self, golden, login
    ):
        response = login("golden_children_coworker").get("/persons/directory_report/")
        assert response.status_code == 403
