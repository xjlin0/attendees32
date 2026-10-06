"""The datagrid_user_organization_attendances page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestDatagridUserOrganizationAttendances:
    def test_a_parent_can_open_their_family_attendances(self, golden, login):
        client = login("golden_member")
        response = client.get("/occasions/datagrid_user_organization_attendances/")
        assert response.status_code == 200
