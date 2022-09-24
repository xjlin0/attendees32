import time

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from schedule.models import Calendar

from attendees.occasions.serializers import CalendarListSerializer


@method_decorator([login_required], name="dispatch")
class OrganizationCalendarsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that may expose all calendars in current users organization filtered by users roles.
    Todo 20220924 make this API public and use domain name/Site as organization indicator
    """

    serializer_class = CalendarListSerializer

    def get_queryset(self):
        user_organization = self.request.user.organization
        pk = self.kwargs.get("pk")
        distinction = self.request.query_params.get("distinction", "source")
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        if user_organization:
            organization_acronym = user_organization.infos.get('acronym').strip()
            extra_filter = Q(slug__istartswith=organization_acronym)
            extra_filter.add(Q(calendarrelation__distinction=distinction), Q.AND)

            if pk:
                extra_filter.add(Q(id=pk), Q.AND)

            if search_value and search_expression == 'name' and search_operation == 'contains':
                extra_filter.add(Q(name__icontains=search_value), Q.AND)

            if not self.request.user.can_see_all_organizational_meets_attendees():
                extra_filter.add(
                    (Q(calendarrelation__content_type=ContentType.objects.filter(model='organization').first().id)
                     &
                     Q(calendarrelation__object_id=user_organization.id
                       )
                     ), Q.OR)

                extra_filter.add(
                    (Q(calendarrelation__content_type=ContentType.objects.filter(model='user').first().id)
                     &
                     Q(calendarrelation__object_id=self.request.user.id
                       )
                     ), Q.OR)

            return Calendar.objects.filter(extra_filter)

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Has your account assigned an organization?"
            )


api_organization_calendars_viewset = OrganizationCalendarsViewSet
