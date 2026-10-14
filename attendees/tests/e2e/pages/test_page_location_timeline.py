"""The location_timeline page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestLocationTimeline:
    def test_the_location_timeline_renders(self, golden, login):
        client = login("golden_data_organizer")
        assert client.get("/occasions/location_timeline/").status_code == 200
