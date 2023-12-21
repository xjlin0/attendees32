import time, pytz

from django.contrib.auth.decorators import login_required
# from django.db.models.aggregates import Count
from django.db.models import Q, Count
from django.contrib.postgres.aggregates.general import StringAgg
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.models import Attendance
from attendees.occasions.serializers import AttendanceStatsSerializer
from attendees.occasions.services import AttendanceService
from attendees.persons.models import Utility


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetCharacterAttendanceStatsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Stats of Attendance to be returned
    """

    serializer_class = AttendanceStatsSerializer

    def get_queryset(self):
        if self.request.user.organization:
            # search_value = self.request.query_params.get("searchValue")
            # search_expression = self.request.query_params.get("searchExpr")
            # search_operation = self.request.query_params.get("searchOperation")
            start = self.request.query_params.get("start")
            finish = self.request.query_params.get("finish")
            characters = self.request.query_params.getlist("characters[]", [])
            teams = self.request.query_params.getlist("teams[]", [])

            filters = Q(gathering__meet__slug__in=self.request.query_params.getlist("meets[]", [])).add(
                    Q(gathering__meet__assembly__division__organization=self.request.user.organization), Q.AND).add(
                    Q(category__in=self.request.query_params.getlist("categories[]", [])), Q.AND)
            # if search_value and search_expression == 'display_name' and search_operation == 'contains':
            #     extra_filter.add(Q(display_name__icontains=search_value), Q.AND)

            if start:
                filters.add((Q(gathering__finish__gte=start)), Q.AND)
            if finish:
                filters.add((Q(gathering__start__lte=finish)), Q.AND)
            if characters:
                filters.add(Q(character__slug__in=characters), Q.AND)
            if teams:
                filters.add(Q(team__in=teams), Q.AND)

            return Attendance.objects.select_related(
                "character",
                "team",
                "attending",
                "gathering",
                "attending__attendee",
            ).filter(filters).values(
                'attending__attendee',
                'attending__attendee__infos__names__original',
            ).annotate(
              count=Count('attending__attendee'),
              characters=StringAgg('character__display_name',delimiter=", ", distinct=True, default=None),
              teams=StringAgg('team__display_name', delimiter=", ", distinct=True, default=None),
            ).order_by('-count', 'attending__attendee__infos__names__original')

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Has your account assigned an organization?"
            )


api_organization_meet_character_attendance_stats_viewset = ApiOrganizationMeetCharacterAttendanceStatsViewSet
