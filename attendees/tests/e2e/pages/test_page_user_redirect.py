"""The user_redirect page against the golden congregation."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestUserRedirect:
    def test_it_redirects_to_the_users_profile(self, golden, login):
        assert login("golden_member").get(reverse("users:redirect")).status_code == 302
