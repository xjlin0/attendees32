import pytest
import pytz
from django.utils import timezone
from django.test import RequestFactory
from attendees.middleware import EarlyApiAuthMiddleware, TimezoneMiddleware, XForwardedForMiddleware

class TestTimezoneMiddleware:
    def test_timezone_middleware_with_cookie(self):
        # Mock get_response function
        def get_response(request):
            return "response"

        middleware = TimezoneMiddleware(get_response)
        rf = RequestFactory()
        request = rf.get('/')
        
        # Set the timezone cookie
        request.COOKIES['timezone'] = 'Asia/Taipei'
        
        middleware(request)
        
        # Check if the timezone was activated correctly
        assert timezone.get_current_timezone_name() == 'Asia/Taipei'

    def test_timezone_middleware_default(self, settings):
        # Set a default timezone in settings
        settings.CLIENT_DEFAULT_TIME_ZONE = 'America/New_York'
        
        def get_response(request):
            return "response"

        middleware = TimezoneMiddleware(get_response)
        rf = RequestFactory()
        request = rf.get('/')
        
        # No cookie set
        middleware(request)
        
        # Check if the default timezone was activated
        assert timezone.get_current_timezone_name() == 'America/New_York'


class TestXForwardedForMiddleware:
    def test_x_forwarded_for_middleware_single_ip(self):
        def get_response(request):
            return "response"

        middleware = XForwardedForMiddleware(get_response)
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='172.24.0.1', HTTP_X_FORWARDED_FOR='203.0.113.55')

        middleware(request)
        assert request.META['REMOTE_ADDR'] == '203.0.113.55'

    def test_x_forwarded_for_middleware_multiple_ips(self):
        def get_response(request):
            return "response"

        middleware = XForwardedForMiddleware(get_response)
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='172.24.0.1', HTTP_X_FORWARDED_FOR='198.51.100.22, 172.24.0.1')

        middleware(request)
        assert request.META['REMOTE_ADDR'] == '198.51.100.22'

    def test_x_forwarded_for_middleware_no_header(self):
        def get_response(request):
            return "response"

        middleware = XForwardedForMiddleware(get_response)
        rf = RequestFactory()
        request = rf.get('/', REMOTE_ADDR='127.0.0.1')

        middleware(request)
        assert request.META['REMOTE_ADDR'] == '127.0.0.1'


class TestEarlyApiAuthMiddleware:
    TOKEN = "0123456789abcdef0123456789abcdef01234567"

    def _call(self, path="/persons/api/attendee_attendings/", **extra):
        def get_response(request):
            return "passed through"

        request = RequestFactory().get(path, **extra)
        return EarlyApiAuthMiddleware(get_response)(request)

    def test_an_api_request_without_credentials_is_refused(self):
        response = self._call()
        assert response.status_code == 403

    @pytest.mark.parametrize("header", ["Token null", "Token undefined", "Token ", "Bearer x", "Token " + "g" * 40])
    def test_a_malformed_token_is_refused(self, header):
        assert self._call(HTTP_AUTHORIZATION=header).status_code == 403

    def test_a_well_formed_token_passes_through(self):
        assert self._call(HTTP_AUTHORIZATION=f"Token {self.TOKEN}") == "passed through"

    def test_a_well_formed_session_cookie_passes_through(self, settings):
        request = RequestFactory().get("/persons/api/attendee_attendings/")
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "abcdefghijklmnopqrstuvwxyz012345"
        assert EarlyApiAuthMiddleware(lambda r: "passed through")(request) == "passed through"

    def test_a_malformed_session_cookie_is_refused(self, settings):
        request = RequestFactory().get("/persons/api/attendee_attendings/")
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "null"
        assert EarlyApiAuthMiddleware(lambda r: "passed through")(request).status_code == 403

    @pytest.mark.parametrize("path", ["/", "/accounts/login/", "/auth-token/", "/persons/attendees/"])
    def test_other_paths_are_untouched(self, path):
        assert self._call(path=path) == "passed through"


class TestApiRefusalNeedsNoDatabase:
    """Through the whole middleware stack, with database access forbidden:
    pytest-django fails the test if anything opens a connection."""

    @pytest.mark.parametrize("path", [
        "/persons/api/attendee_attendings/",
        "/occasions/api/organization_meets/",
        "/whereabouts/api/user_divisions/",
        "/api/users/",
    ])
    def test_an_anonymous_api_call_is_refused_without_a_query(self, client, path):
        assert client.get(path).status_code == 403

    def test_a_null_token_is_refused_without_a_query(self, client):
        response = client.get("/persons/api/attendee_attendings/", HTTP_AUTHORIZATION="Token null")
        assert response.status_code == 403

