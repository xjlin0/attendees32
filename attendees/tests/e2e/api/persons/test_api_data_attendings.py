"""``/persons/api/<division>/<assembly>/data_attendings/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import DIVISION_DATA

pytestmark = pytest.mark.django_db


class TestDataAttendings:
    def test_data_attendings_are_scoped_to_the_data_division(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            f"/persons/api/{DIVISION_DATA}/{AssemblySlugs.CONGREGATION_DATA}"
            "/data_attendings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE},
        )
        assert response.status_code == 200
