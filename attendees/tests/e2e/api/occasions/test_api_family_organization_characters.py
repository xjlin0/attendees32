"""``/occasions/api/family_organization_characters/`` against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestFamilyOrganizationCharacters:
    def test_family_characters_are_listed(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/occasions/api/family_organization_characters/")
        assert response.status_code == 200
