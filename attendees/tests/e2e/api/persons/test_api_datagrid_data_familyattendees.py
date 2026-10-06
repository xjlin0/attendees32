"""``/persons/api/datagrid_data_familyattendees/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import FolkCategory
from attendees.tests.golden.constants import Relations
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestDatagridDataFamilyattendees:
    def test_family_membership_rows_carry_the_role(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.get(
            "/persons/api/datagrid_data_familyattendees/",
            {"categoryId": FolkCategory.FAMILY},
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert {row["attendee"] for row in rows} >= {
            str(golden.attendee("chen_zhiming").id),
            str(golden.attendee("chen_joshua").id),
        }
        assert {row["role"] for row in rows} >= {Relations.HUSBAND, Relations.SON}
        assert any(
            row["folk"]["display_name"].startswith("陳志明家") for row in rows
        )

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = target(token_client("golden_data_organizer"), golden.attendee("chen_grace"))
        response = client.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY})
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY})
        assert response.status_code == 403

    def test_the_spy_guard_holds_for_a_token_client(self, golden, token_client):
        """A token client is held to the same rules as a session: an ordinary
        member may not reach a stranger's record, and a deleted attendee is a 404."""
        stranger = target(token_client("golden_crossing_member"), golden.attendee("chen_grace"))
        assert stranger.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY}).status_code == 403

        deleted = target(token_client("golden_data_organizer"), golden.attendee("peng_jinlong"))
        assert deleted.get("/persons/api/datagrid_data_familyattendees/", {"categoryId": FolkCategory.FAMILY}).status_code == 404
