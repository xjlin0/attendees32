"""``/persons/api/<division>/<assembly>/assembly_meet_attendings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import DIVISION_JUNIOR

pytestmark = pytest.mark.django_db


class TestAssemblyMeetAttendings:
    def test_assembly_scoped_attendings_answer(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            f"/persons/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}/assembly_meet_attendings/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200
