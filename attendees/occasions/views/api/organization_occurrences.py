import time

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
        user_organization = self.request.user.organization
        calendar_id = self.request.query_params.get("calendar", user_organization.infos.get('default_calendar', 0))
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        pk = self.kwargs.get("pk")
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        if user_organization:
            organization_acronym = user_organization.infos.get('acronym').strip()
            calendar = Calendar.objects.filter(slug__istartswith=organization_acronym, pk=calendar_id).first()

            if calendar:
                events = Event.objects.filter(calendar=calendar.id)
                period = Period(events, start, end)
                return period.get_occurrences()

            else:
                time.sleep(2)
                raise AuthenticationFailed(
                    detail="Has your organization assigned a calendar?"
                )


api_organization_occurrences_viewset = OccurrencesCalendarsViewSet
