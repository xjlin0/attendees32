"""The datagrid_assembly_all_attendings page against the golden congregation."""

import pytest

from attendees.tests.golden.constants import AssemblySlugs
from attendees.tests.golden.constants import DIVISION_SLUGS

pytestmark = pytest.mark.django_db


class TestDatagridAssemblyAllAttendings:
    def test_the_assembly_attendings_page_lists_junior_meets(self, golden, login):
        client = login("golden_children_organizer")
        response = client.get(
            f"/persons/{DIVISION_SLUGS[3]}/{AssemblySlugs.JUNIOR_REGULAR}"
            "/datagrid_assembly_all_attendings/"
        )
        assert response.status_code == 200
        names = {meet["display_name"] for meet in response.context["available_meets_json"]}
        assert {"The Rock", "Little foot"} <= names
