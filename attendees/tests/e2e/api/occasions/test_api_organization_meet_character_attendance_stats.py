"""``/occasions/api/organization_meet_character_attendance_stats/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AttendanceCategory
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import CONGREGATION_SLUG, window

pytestmark = pytest.mark.django_db


class TestOrganizationMeetCharacterAttendanceStats:
    def test_attendance_counts_are_grouped_per_person(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_character_attendance_stats/",
            {
                "meets[]": MeetSlugs.CHINESE_SERVICE,
                "characters[]": CONGREGATION_SLUG,
                "categories[]": AttendanceCategory.ATTENDED,
                **window(),
                "take": 25,
            },
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert rows
        assert all(row["count"] >= 1 for row in rows)
        assert max(row["count"] for row in rows) <= 8  # only eight Sundays exist

    def test_statistics_can_be_narrowed_to_one_name(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_character_attendance_stats/",
            {
                "meets[]": MeetSlugs.CHINESE_SERVICE,
                "characters[]": CONGREGATION_SLUG,
                **window(),
                "filter": str([["attending_name", "contains", "Zhiming"]]),
            },
        )
        assert response.status_code == 200
