import time, pytz
from datetime import datetime
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from schedule.models import Calendar, Event
from schedule.periods import Period
from urllib import parse

from attendees.occasions.serializers import OccurrenceSerializer


@method_decorator([login_required], name="dispatch")
class OccurrencesCalendarsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that may expose all calendars in current users organization filtered by users roles.
    Todo 20220924 make this API public and use domain name/Site as organization indicator
    """

    serializer_class = OccurrenceSerializer

    def get_queryset(self):
        iso_time_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        user_organization = self.request.user.organization
        user_organization_calendar = user_organization.calendar_relations.filter(distinction='source').first().calendar
        calendar_id = self.request.query_params.get("calendar")
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        pk = self.kwargs.get("pk")
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        if user_organization and start and end:
            tzname = (
                self.request.COOKIES.get("timezone")
                or user_organization.infos["default_time_zone"]
                or settings.CLIENT_DEFAULT_TIME_ZONE
            )
            user_time_zone = pytz.timezone(parse.unquote(tzname))
            organization_acronym = user_organization.infos.get('acronym').strip()
            filters = Q(slug__istartswith=organization_acronym)
            if calendar_id:
                filters.add(Q(pk=calendar_id), Q.AND)
            else:  # UI need all location calendars but not organization calendar which duplicates every events
                filters.add(~Q(pk=user_organization_calendar.id), Q.AND)
            calendars = Calendar.objects.filter(filters)

            if calendars:
                user_organization_calendar_all_day_events = Event.objects.filter(calendar=user_organization_calendar, description__startswith='allDay:')
                events = Event.objects.filter(calendar__in=calendars)

                period = Period(
                    events,
                    datetime.strptime(start, iso_time_format),
                    datetime.strptime(end, iso_time_format),
                    tzinfo=user_time_zone,
                )

                if int(calendar_id) == user_organization_calendar.id:
                    return period.get_occurrences()

                else:   # UI is showing other calendar, needs all day events
                    all_day_period = Period(
                        user_organization_calendar_all_day_events,
                        datetime.strptime(start, iso_time_format),
                        datetime.strptime(end, iso_time_format),
                        tzinfo=user_time_zone,
                    )

                    return period.get_occurrences() + all_day_period.get_occurrences()

            else:
                time.sleep(2)
                raise AuthenticationFailed(
                    detail="Has your organization assigned a calendar? Please specify start and end time!"
                )
        return []


api_organization_occurrences_viewset = OccurrencesCalendarsViewSet
