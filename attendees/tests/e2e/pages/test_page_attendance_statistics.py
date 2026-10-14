"""The attendance_statistics page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendanceStatistics:
    def test_the_statistics_page_renders(self, golden, login):
        client = login("golden_data_organizer")
        assert client.get("/occasions/attendance_statistics/").status_code == 200
