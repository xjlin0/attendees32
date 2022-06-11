import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.aggregates import Count
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.persons.models import Utility, AttendingMeet
from attendees.persons.serializers import AttendingMeetEtcSerializer
from attendees.persons.services import AttendingMeetService


class ApiOrganizationMeetCharacterAttendingMeetsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    Todo 20220514: replace LoginRequiredMixin with SpyGuard and needed seeds json
    Todo 20220514: make API returns only current users attendinmeets if not admin
    """

    serializer_class = AttendingMeetEtcSerializer

    def list(self, request, *args, **kwargs):
        group_string = request.query_params.get(
            "group", '[{}]'
        )  # [{"selector":"meet","desc":false,"isExpanded":false}] if grouping
        group_column = json.loads(group_string)[0].get('selector')
        current_user_organization = request.user.organization
        meet_slugs = request.query_params.getlist("meets[]", [])
        character_slugs = request.query_params.getlist("characters[]", [])
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            print("hi 36")
            if group_column:
                print("hi 38")
                counters = AttendingMeet.objects.filter(
                    meet__slug__in=meet_slugs,
                    character__slug__in=character_slugs,
                    meet__assembly__division__organization=current_user_organization,
                ).values(group_column).order_by(group_column).annotate(count=Count(group_column))
                return Response(Utility.group_count(group_column, counters))

            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, group_column)
            )
        print("hi 50")
        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, group_column))

    def get_queryset(self):
        current_user = self.request.user
        current_user_organization = current_user.organization

        if current_user_organization:
            pk = self.kwargs.get("pk")
            group_string = self.request.query_params.get(
                "group"
            )  # [{"selector":"meet","desc":false,"isExpanded":false}] if grouping
            orderby_list = json.loads(
                self.request.query_params.get(
                    "sort",
                    '[{"selector":"meet","desc":false},{"selector":"start","desc":false}]',
                )
            )  # order_by('meet','start')
            # Todo: add group column to orderby_list
            if pk:
                filters = {
                    'pk': pk,
                    'meet__assembly__division__organization': current_user_organization,
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
                print("hi 75 here is group_string", group_string)
                qs = AttendingMeetService.by_organization_meet_characters(
                    current_user=self.request.user,
                    meet_slugs=self.request.query_params.getlist("meets[]", []),
                    character_slugs=self.request.query_params.getlist("characters[]", []),
                    start=self.request.query_params.get("start"),
                    finish=self.request.query_params.get("finish"),
                    orderbys=orderby_list,
                    filter=self.request.query_params.get("filter"),
                )
                print("hi 81 here is qs.count()", qs.count())
                return qs

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_character_attendingmeets_viewset = ApiOrganizationMeetCharacterAttendingMeetsViewSet
