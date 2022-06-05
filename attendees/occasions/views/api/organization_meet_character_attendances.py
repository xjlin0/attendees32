import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.serializers import AttendanceEtcSerializer
from attendees.occasions.services import AttendanceService
from attendees.persons.models import Utility, AttendingMeet


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
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, json.loads(group_string)[0].get('selector'))
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, json.loads(group_string)[0].get('selector')))

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
                filters = {
                    'pk': pk,
                    'gathering__meet__assembly__division__organization': current_user_organization,
                }
                if not current_user.can_see_all_organizational_meets_attendees():
                    filters['attendings__attendee'] = current_user.attendee

                return AttendingMeet.objects.filter(**filters)

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
                    orderbys=orderby_list,
                    filter=self.request.query_params.get("filter"),
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_character_attendances_viewset = ApiOrganizationMeetCharacterAttendancesViewSet
