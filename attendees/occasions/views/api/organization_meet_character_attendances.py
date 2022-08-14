import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.aggregates import Count
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.models import Attendance
from attendees.occasions.serializers import AttendanceEtcSerializer
from attendees.occasions.services import AttendanceService
from attendees.persons.models import Utility


class ApiOrganizationMeetCharacterAttendancesViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    Todo 20220514: replace LoginRequiredMixin with SpyGuard and needed seeds json
    Todo 20220514: make API returns only current users attendances if not admin
    """

    serializer_class = AttendanceEtcSerializer

    def list(self, request, *args, **kwargs):
        group_string = request.query_params.get(
            "group", '[{}]'
        )  # [{"selector":"gathering","desc":false,"isExpanded":false}] if grouping
        group_column = json.loads(group_string)[0].get('selector')
        search_value = json.loads(self.request.query_params.get("filter", "[[null]]"))[0][-1]  # could be [[null,"contains","jack"],"or",[null,"contains","jack"]] or [[[null,"contains","jack"],"or",[null,"contains","jack"]],"and",["gathering__meet__assembly","=",5]]
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            if group_column:
                filters = Q(gathering__meet__slug__in=request.query_params.getlist("meets[]", [])).add(
                    Q(character__slug__in=request.query_params.getlist("characters[]", [])), Q.AND).add(
                    Q(gathering__meet__assembly__division__organization=request.user.organization), Q.AND)

                if isinstance(search_value, str):
                    filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
                                 |
                                 Q(attending__attendee__infos__icontains=search_value)
                                 |
                                 Q(gathering__display_name__icontains=search_value)
                                 |
                                 Q(infos__icontains=search_value)), Q.AND)

                counters = Attendance.objects.filter(filters).values(group_column).order_by(group_column).annotate(count=Count(group_column))
                return Response(Utility.group_count(group_column, counters))

            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, group_column)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, group_column))

    def get_queryset(self):
        current_user = self.request.user
        current_user_organization = current_user.organization

        if current_user_organization:
            pk = self.kwargs.get("pk")
            group_string = self.request.query_params.get(
                "group"
            )  # [{"selector":"gathering","desc":false,"isExpanded":false}] if grouping
            orderby_list = json.loads(
                self.request.query_params.get(
                    "sort",
                    '[{"selector":"gathering","desc":false},{"selector":"start","desc":false}]',
                )
            )  # order_by('gathering','start')
            # Todo: add group colume to orderby_list
            if pk:
                filters = Q(
                    gathering__meet__assembly__division__organization=current_user_organization
                ).add(Q(pk=pk), Q.AND)
                if not current_user.can_see_all_organizational_meets_attendees():
                    filters.add((Q(attending__attendee__in=current_user.attendee.scheduling_attendees())
                                 |
                                 Q(attending__registration__registrant=current_user.attendee)), Q.AND)

                return Attendance.objects.filter(filters)

            else:
                if group_string:
                    groups = json.loads(group_string)
                    orderby_list.insert(
                        0, {"selector": groups[0]["selector"], "desc": groups[0]["desc"]}
                    )

                return AttendanceService.by_organization_meet_characters(
                    current_user=self.request.user,
                    meet_slugs=self.request.query_params.getlist("meets[]", []),
                    character_slugs=self.request.query_params.getlist("characters[]", []),
                    start=self.request.query_params.get("start"),
                    finish=self.request.query_params.get("finish"),
                    gatherings=self.request.query_params.getlist("gatherings[]", []),
                    orderbys=orderby_list,
                    photo_instead_of_gathering_assembly=self.request.query_params.get("photoInsteadOfGatheringAssembly"),
                    filter=self.request.query_params.get("filter"),
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_character_attendances_viewset = ApiOrganizationMeetCharacterAttendancesViewSet
