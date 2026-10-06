"""``/persons/api/attendee_relationships/`` against the golden congregation."""

import pytest

from attendees.tests.golden.constants import FolkCategory
from attendees.tests.golden.constants import Relations
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestAttendeeRelationships:
    def test_other_relationships_come_from_the_same_endpoint(self, golden, api_login):
        kevin = golden.attendee("xu_kevin")
        client = target(api_login("golden_counselor"), kevin)
        response = client.get(
            "/persons/api/attendee_relationships/",
            {"categoryId": FolkCategory.OTHER},
        )
        assert response.status_code == 200
        roles = {row["role"] for row in response.json()["data"]}
        assert Relations.GUARDIAN in roles
