import pytz
from urllib import parse
from django.utils import timezone
# from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


from django.urls import resolve, Resolver404
from django.http import HttpResponseNotFound
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
