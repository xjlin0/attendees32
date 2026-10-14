"""The user_detail page against the golden congregation."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestUserDetail:
    def test_a_user_can_read_their_own_profile(self, golden, login):
        client = login("golden_member")
        response = client.get(reverse("users:detail", kwargs={"username": "golden_member"}))
        assert response.status_code == 200
