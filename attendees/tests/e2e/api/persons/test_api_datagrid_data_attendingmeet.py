"""``/persons/api/datagrid_data_attendingmeet/`` against the golden congregation."""

import pytest

from attendees.occasions.models import Meet
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestDatagridDataAttendingmeet:
    def test_an_attendees_participations_are_listed(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.get("/persons/api/datagrid_data_attendingmeet/")
        assert response.status_code == 200
        meet_ids = {row["meet"] for row in response.json()["data"]}
        assert Meet.objects.get(slug=MeetSlugs.CHINESE_SERVICE).id in meet_ids
        assert Meet.objects.get(slug=MeetSlugs.DIRECTORY).id in meet_ids
