"""The Django admin against the golden congregation."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestAdmin:
    def test_a_superuser_reaches_the_admin_index(self, golden, login):
        client = login("golden_superuser")
        response = client.get("/admin123/")
        assert response.status_code == 200
        assert b"Attendees" in response.content or b"attendees" in response.content

    def test_an_ordinary_member_is_turned_away_from_the_admin(self, golden, login):
        client = login("golden_member")
        response = client.get("/admin123/", follow=False)
        # Django's admin sends a non-staff user to its own login page.
        assert response.status_code in {302, 403}
        if response.status_code == 302:
            assert "login" in response["Location"]

    def test_the_attendee_changelist_opens_and_finds_a_person(self, golden, login):
        client = login("golden_superuser")
        response = client.get("/admin123/persons/attendee/", {"q": "Zhiming"})
        assert response.status_code == 200
        assert b"Zhiming" in response.content

    def test_the_admin_url_is_not_the_default_one(self, golden):
        """A guessable admin path is a free door to rattle."""
        assert reverse("admin:index") != "/admin/"
