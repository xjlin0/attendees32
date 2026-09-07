import pytest
import pytz
from django.utils import timezone
from django.test import RequestFactory
from attendees.middleware import TimezoneMiddleware, XForwardedForMiddleware

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
