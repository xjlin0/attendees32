"""The roster page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestRoster:
    def test_the_roster_page_renders_for_a_coworker(self, golden, login):
        client = login("golden_children_coworker")
        assert client.get("/occasions/roster/").status_code == 200
