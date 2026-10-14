"""The attendances page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestAttendances:
    def test_the_attendances_page_renders(self, golden, login):
        client = login("golden_data_organizer")
        assert client.get("/occasions/attendances/").status_code == 200
