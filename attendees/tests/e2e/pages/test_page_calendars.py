"""The calendars page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestCalendars:
    def test_the_calendar_page_renders(self, golden, login):
        client = login("golden_member")
        assert client.get("/occasions/calendars/").status_code == 200
