import time, ast

from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, CharField, Value, When, Case, Count
from django.db.models.functions import Concat, Trim
from django.contrib.postgres.aggregates.general import StringAgg
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.utils import json

from attendees.occasions.models import Attendance
from attendees.occasions.serializers import AttendanceStatsSerializer
from attendees.occasions.services import AttendanceService


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetCharacterAttendanceStatsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Stats of Attendance to be returned, currently not support sorting
    and search only support attendee's names
    """

    serializer_class = AttendanceStatsSerializer

    def get_queryset(self):
        user_organization = self.request.user.organization
        if user_organization:
            orderby_list = json.loads(
                self.request.query_params.get(
                    "sort",
                    '[{"selector":"count","desc":true},{"selector":"attending_name","desc":false}]',
                )
            )
            name_search = ast.literal_eval(self.request.query_params.get("filter", "[[None]]"))

            return AttendanceService.attendance_count(
                    user_organization=user_organization,
                    meet_slugs=self.request.query_params.getlist("meets[]", []),
                    character_slugs=self.request.query_params.getlist("characters[]", []),
                    team_ids=self.request.query_params.getlist("teams[]", []),
                    category_ids=self.request.query_params.getlist("categories[]", []),
                    start=self.request.query_params.get("start"),
                    finish=self.request.query_params.get("finish"),
                    orderbys=orderby_list,
                    name_search=name_search,
                )  # The start/finish will filter on Gathering instead of Attendance!!

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Has your account assigned an organization?"
            )


api_organization_meet_character_attendance_stats_viewset = ApiOrganizationMeetCharacterAttendanceStatsViewSet
