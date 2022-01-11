from urllib import parse

import pytz
from django.conf import settings
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class TimezoneMiddleware(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        tzname = request.COOKIES.get("timezone") or settings.CLIENT_DEFAULT_TIME_ZONE
        timezone.activate(pytz.timezone(parse.unquote(tzname)))
