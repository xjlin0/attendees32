import re

import pytz
from urllib import parse
from django.utils import timezone
# from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


from django.urls import resolve, Resolver404
from django.http import HttpResponseNotFound, JsonResponse
from django.template.loader import render_to_string

class Early404Middleware:
    """
    Scans the requested URL against urls.py. If it doesn't match any valid path, 
    immediately returns a lightweight 404 response. This runs high in the middleware 
    stack to completely bypass DB queries caused by other middlewares (like pghistory).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            resolve(request.path_info)
        except Resolver404:
            return HttpResponseNotFound(render_to_string("404_light.html", request=None))
        return self.get_response(request)


class EarlyApiAuthMiddleware:
    """
    Refuses API requests that carry no plausible credentials before anything
    touches the database, with the same 403 DRF would give.

    With ATOMIC_REQUESTS every request that reaches a view opens a database
    connection, whether or not it is then refused, and TokenAuthentication looks
    up any token it is sent, "Token null" included. A flood of such requests can
    use up every connection. So an API request must carry a session cookie
    shaped like a session key, or an Authorization header shaped like a DRF
    token; whether either is genuine is still DRF's call.
    """
    API_PATH = re.compile(r"^/(?:api|persons/api|occasions/api|whereabouts/api)/")
    TOKEN_HEADER = re.compile(r"^token [0-9a-f]{40}$", re.IGNORECASE)
    SESSION_KEY = re.compile(r"^[a-z0-9]{32}$")  # django.contrib.sessions key alphabet

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.API_PATH.match(request.path_info) and not self.has_plausible_credentials(request):
            return JsonResponse(
                {"detail": "Authentication credentials were not provided."}, status=403
            )
        return self.get_response(request)

    def has_plausible_credentials(self, request):
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, "")
        authorization = request.META.get("HTTP_AUTHORIZATION", "")
        return bool(
            self.SESSION_KEY.match(session_key) or self.TOKEN_HEADER.match(authorization)
        )


class TimezoneMiddleware:

    # @staticmethod
    # def process_request(request):
    #     tzname = request.COOKIES.get('timezone') or settings.CLIENT_DEFAULT_TIME_ZONE
    #     timezone.activate(pytz.timezone(parse.unquote(tzname)))

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.COOKIES.get('timezone') or settings.CLIENT_DEFAULT_TIME_ZONE
        timezone.activate(pytz.timezone(parse.unquote(tzname)))
        return self.get_response(request)


class XForwardedForMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "HTTP_X_FORWARDED_FOR" in request.META:
            request.META["REMOTE_ADDR"] = request.META["HTTP_X_FORWARDED_FOR"].split(",")[0].strip()
        return self.get_response(request)
