"""``/persons/api/<division>/<assembly>/assembly_meet_attendees/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import DIVISION_JUNIOR

pytestmark = pytest.mark.django_db


class TestAssemblyMeetAttendees:
    def test_assembly_scoped_attendees_are_listed(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            f"/persons/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}/assembly_meet_attendees/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 10
