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

    @pytest.mark.django_db
    def test_defensive_404_handler_with_session_cookie(self):
        """
        When a session cookie is present, defensive_404_handler delegates to standard Django
        render with 404.html and includes the exception context.
        """
        factory = RequestFactory()
        request = factory.get("/non_existent_page")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        request.COOKIES = {cookie_name: "dummy_session_id"}

        with patch("attendees.utils.view_helpers.render") as mock_render:
            defensive_404_handler(request, exception="Test Exception")
            mock_render.assert_called_once()
            args, kwargs = mock_render.call_args
            assert args[0] == request
            assert args[1] == "404.html"
            assert args[2] == {"exception": "Test Exception"}
            assert kwargs == {"status": 404}
