"""The home page against the golden congregation."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestHome:
    def test_it_is_public(self, client):
        assert client.get(reverse("home")).status_code == 200
