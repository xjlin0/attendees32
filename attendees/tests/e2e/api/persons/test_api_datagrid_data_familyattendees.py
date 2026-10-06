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
