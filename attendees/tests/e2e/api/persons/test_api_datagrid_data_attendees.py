"""``/persons/api/datagrid_data_attendees/`` against the golden congregation."""

import json

import pytest

from attendees.tests.golden.constants import MeetSlugs

pytestmark = pytest.mark.django_db


class TestDatagridDataAttendees:
    def test_the_datagrid_roster_filters_by_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/datagrid_data_attendees/",
            {
                "filter": json.dumps(
                    ["attendings__meets__slug", "=", MeetSlugs.ENGLISH_SERVICE]
                )
            },
        )
        assert response.status_code == 200
        # 135 people are on the English service roster (100 adults, 25 youth and
        # the 10 bilingual attenders); the datagrid counts only participations
        # that have not finished, so the 15 inactive ones drop out.
        assert response.json()["totalCount"] == 120

    def test_the_datagrid_roster_accepts_a_devextreme_filter(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/datagrid_data_attendees/",
            {"filter": json.dumps(["last_name", "=", "Tsai"])},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 4

    def test_the_dead_are_excluded_unless_asked_for(self, golden, api_login):
        client = api_login("golden_data_organizer")
        without = client.get("/persons/api/datagrid_data_attendees/").json()["totalCount"]
        with_dead = client.get(
            "/persons/api/datagrid_data_attendees/?include_dead=true"
        ).json()["totalCount"]
        assert with_dead > without
