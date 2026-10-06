"""The gatherings page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestGatherings:
    def test_the_gatherings_page_renders(self, golden, login):
        client = login("golden_data_organizer")
        assert client.get("/occasions/gatherings/").status_code == 200
