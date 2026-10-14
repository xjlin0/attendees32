"""``/occasions/api/<division>/<assembly>/assembly_meet_attendances/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import DIVISION_JUNIOR, JUNIOR_STUDENT_SLUG, window

pytestmark = pytest.mark.django_db


class TestAssemblyMeetAttendances:
    def test_assembly_scoped_attendances(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            f"/occasions/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}"
            "/assembly_meet_attendances/",
            {"meets[]": MeetSlugs.THE_ROCK, "characters[]": JUNIOR_STUDENT_SLUG,
             **window()},
        )
        assert response.status_code == 200
