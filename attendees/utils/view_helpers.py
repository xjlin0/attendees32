import time

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.http import HttpResponseNotFound
from django.shortcuts import _get_queryset, render
from django.template.loader import render_to_string


def defensive_404_handler(request, exception=None, *args, **kwargs):
    """
    Defensive 404 error handler that checks for a session cookie before rendering base.html
    or accessing context processors/database connections.
    If no session cookie is present (e.g. bots, scrapers, anonymous probing), returns a lightweight
    standalone HTML response without evaluating context processors or making database queries.
    """
    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    if cookie_name not in request.COOKIES:
        return HttpResponseNotFound(
            render_to_string("404_light.html", request=None)
        )
    return render(request, "404.html", {"exception": exception}, status=404)


def get_object_or_delayed_403(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except ObjectDoesNotExist:
        time.sleep(2)
        raise ObjectDoesNotExist
    except MultipleObjectsReturned:
        raise MultipleObjectsReturned
