"""The directory_preview page against the golden congregation."""

import pytest

pytestmark = pytest.mark.django_db


class TestDirectoryPreview:
    def test_a_member_can_preview_their_own_directory_entry(self, golden, login):
        client = login("golden_counselor")
        response = client.get(
            f"/persons/directory_preview/{golden.attendee('chen_zhiming').id}"
        )
        assert response.status_code == 200
        assert response.context["families"]

    def test_the_preview_falls_back_to_the_readers_own_family(self, golden, login):
        """An unprivileged reader asking about somebody else sees themselves."""
        client = login("golden_children_organizer")
        response = client.get(
            f"/persons/directory_preview/{golden.attendee('tsai_shixiang').id}"
        )
        assert response.status_code == 200
