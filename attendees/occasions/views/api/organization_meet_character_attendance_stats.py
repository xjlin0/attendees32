import time, ast

from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, CharField, Value, When, Case, Count
from django.db.models.functions import Concat, Trim
from django.contrib.postgres.aggregates.general import StringAgg
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.models import Attendance
from attendees.occasions.serializers import AttendanceStatsSerializer


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetCharacterAttendanceStatsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Stats of Attendance to be returned, currently not support sorting
    and search only support attendee's names
    """

    serializer_class = AttendanceStatsSerializer

    def get_queryset(self):
        if self.request.user.organization:
            name_search = ast.literal_eval(self.request.query_params.get("filter", "[[None]]"))
            start = self.request.query_params.get("start")
            finish = self.request.query_params.get("finish")
            characters = self.request.query_params.getlist("characters[]", [])
            teams = self.request.query_params.getlist("teams[]", [])

            filters = Q(gathering__meet__slug__in=self.request.query_params.getlist("meets[]", [])).add(
                    Q(gathering__meet__assembly__division__organization=self.request.user.organization), Q.AND).add(
                    Q(category__in=self.request.query_params.getlist("categories[]", [])), Q.AND)
            if name_search[-1][-1]:
                filters.add(Q(Q(attending__attendee__infos__names__original__icontains=name_search[-1][-1])
                              |
                              Q(attending__attendee__infos__names__traditional__icontains=name_search[-1][-1])
                              |
                              Q(attending__attendee__infos__names__simplified__icontains=name_search[-1][-1])), Q.AND)

            if start:
                filters.add((Q(gathering__finish__gte=start)), Q.AND)
            if finish:
                filters.add((Q(gathering__start__lte=finish)), Q.AND)
            if characters:
                filters.add(Q(character__slug__in=characters), Q.AND)
            if teams:
                filters.add(Q(team__in=teams), Q.AND)

            attendee_name = Trim(
                Concat(
                    Trim(Concat("attending__attendee__first_name", Value(' '), "attending__attendee__last_name",
                                output_field=CharField())),
                    Value(' '),
                    Trim(Concat("attending__attendee__last_name2", "attending__attendee__first_name2",
                                output_field=CharField())),
                    output_field=CharField()
                )
            )

            register_name = Trim(
                Concat(
                    Trim(Concat("attending__registration__registrant__first_name", Value(' '),
                                "attending__registration__registrant__last_name", output_field=CharField())),
                    Value(' '),
                    Trim(Concat("attending__registration__registrant__last_name2",
                                "attending__registration__registrant__first_name2", output_field=CharField())),
                    output_field=CharField()
                )
            )

            return Attendance.objects.select_related(
                "character",
                "team",
                "attending",
                "gathering",
                "attending__attendee",
            ).filter(filters).values(
                'attending__attendee',
                'attending__attendee__infos__names__original'
                'attending__registration__registrant_id',
            ).annotate(
              count=Count('attending__attendee'),
              characters=StringAgg('character__display_name',delimiter=", ", distinct=True, default=None),
              teams=StringAgg('team__display_name', delimiter=", ", distinct=True, default=None),
              attending_name=Case(
                  When(attending__registration__isnull=True, then=attendee_name),
                  When(attending__attendee=F('attending__registration__registrant'), then=attendee_name),
                  default=Concat(
                      attendee_name,
                      Value(' by '),
                      register_name,
                      output_field=CharField()
                  ),
                  output_field=CharField()
                ),
            ).order_by('-count', 'attending__attendee__infos__names__original')

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Has your account assigned an organization?"
            )


api_organization_meet_character_attendance_stats_viewset = ApiOrganizationMeetCharacterAttendanceStatsViewSet
