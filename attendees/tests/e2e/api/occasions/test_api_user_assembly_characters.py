"""``/occasions/api/user_assembly_characters/`` against the golden congregation."""

import pytest

from attendees.occasions.models import Assembly
from attendees.tests.golden.constants import AssemblySlugs

pytestmark = pytest.mark.django_db


class TestUserAssemblyCharacters:
    def test_characters_can_be_scoped_to_an_assembly(self, golden, api_login):
        junior = Assembly.objects.get(slug=AssemblySlugs.JUNIOR_REGULAR)
        client = api_login("golden_data_organizer")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get(
            "/occasions/api/user_assembly_characters/",
            {"assemblies[]": junior.pk, "take": 100},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 5
