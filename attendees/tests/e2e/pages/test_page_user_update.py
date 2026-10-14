"""The user_update page against the golden congregation."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestUserUpdate:
    def test_a_user_can_open_their_own_profile_form(self, golden, login):
        assert login("golden_member").get(reverse("users:update")).status_code == 200
