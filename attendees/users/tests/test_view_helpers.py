from unittest.mock import patch

import pytest
from django.conf import settings
from django.test import RequestFactory

from attendees.utils.view_helpers import defensive_404_handler


class TestViewHelpers:

    def test_defensive_404_handler_without_session_cookie_uses_no_db(self):
        """
        Without a session cookie (e.g. unauthenticated bots/probers), defensive_404_handler
        returns 404_light.html without running context processors or database queries.
        Notice this test is intentionally NOT decorated with @pytest.mark.django_db;
        any database query would automatically fail the test.
        """
        factory = RequestFactory()
        request = factory.get("/.ssh/id_dsa")
        request.COOKIES = {}  # No session cookie present

        response = defensive_404_handler(request, exception=Exception("Secret exception"))
        assert response.status_code == 404
        content = response.content.decode("utf-8")
        assert "Page Not Found (404)" in content
        assert "Go Back" in content
        assert "Secret exception" not in content  # Sensitive exceptions hidden from unauthenticated probes

    def test_defensive_404_handler_with_session_cookie_still_uses_no_db(self):
        """
        Even when a session cookie is present, defensive_404_handler must return the 
        lightweight 404_light.html without evaluating context processors or database queries.
        """
        factory = RequestFactory()
        request = factory.get("/non_existent_page")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        request.COOKIES = {cookie_name: "dummy_session_id"}

        response = defensive_404_handler(request, exception=Exception("Secret exception"))
        assert response.status_code == 404
        content = response.content.decode("utf-8")
        assert "Page Not Found (404)" in content
        assert "Go Back" in content
        assert "Secret exception" not in content
