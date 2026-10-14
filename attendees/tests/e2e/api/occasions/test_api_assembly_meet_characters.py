"""``/occasions/api/<division>/<assembly>/assembly_meet_characters/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import DIVISION_JUNIOR

pytestmark = pytest.mark.django_db


class TestAssemblyMeetCharacters:
    def test_assembly_meet_characters_answers_for_the_assembly(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            f"/occasions/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}/assembly_meet_characters/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200
