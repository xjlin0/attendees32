import time
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from schedule.models import Calendar, Event
from schedule.periods import Period

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
        user_organization_calendar = user_organization.calendar_relations.filter(distinction='source').first()
        calendar_id = self.request.query_params.get("calendar", user_organization_calendar and user_organization_calendar.id or 0)
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        pk = self.kwargs.get("pk")
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        if user_organization and start and end:
            start_time = datetime.strptime(start, iso_time_format)
            end_time = datetime.strptime(end, iso_time_format)
            organization_acronym = user_organization.infos.get('acronym').strip()
            calendar = Calendar.objects.filter(slug__istartswith=organization_acronym, pk=calendar_id).first()

            if calendar:
                events = Event.objects.filter(calendar=calendar.id)
                period = Period(events, start_time, end_time)
                return period.get_persisted_occurrences().filter(
                    end__gte=start_time,
                    start__lte=end_time
                )

            else:
                time.sleep(2)
                raise AuthenticationFailed(
                    detail="Has your organization assigned a calendar? Please specify start and end time!"
                )
        return []


api_organization_occurrences_viewset = OccurrencesCalendarsViewSet