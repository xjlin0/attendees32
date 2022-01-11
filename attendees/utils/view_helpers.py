import time

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.shortcuts import _get_queryset


def get_object_or_delayed_403(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except ObjectDoesNotExist:
        time.sleep(2)
        raise ObjectDoesNotExist
    except MultipleObjectsReturned:
        raise MultipleObjectsReturned
