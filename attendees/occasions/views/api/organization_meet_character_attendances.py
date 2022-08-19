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
        start = self.request.query_params.get("start")
        finish = self.request.query_params.get("finish")
        gatherings = self.request.query_params.getlist("gatherings[]", [])
        group_string = request.query_params.get(
            "group", '[{}]'
        )  # [{"selector":"gathering","desc":false,"isExpanded":false}] if grouping
        characters = request.query_params.getlist("characters[]", [])
        group_column = json.loads(group_string)[0].get('selector')
        filter = self.request.query_params.get("filter")


        # if filter:
        #     meet_slugs = request.query_params.getlist("meets[]", [])
        #     filters = AttendeeService.filter_parser(filter, Meet.objects.filter(slug__in=meet_slugs), self.request.user)
        #     queryset = self.filter_queryset(self.get_queryset().filter(filters))
        # else:
        #     queryset = self.filter_queryset(self.get_queryset())
        search_value = json.loads(self.request.query_params.get("filter", "[[null]]"))[0][-1]  # could be [[null,"contains","jack"],"or",[null,"contains","jack"]] or [[[null,"contains","jack"],"or",[null,"contains","jack"]],"and",["gathering__meet__assembly","=",5]]
        queryset = self.filter_queryset(self.get_queryset())
        print("hi 46 here is queryset.count(): ", queryset.count())
        page = self.paginate_queryset(queryset)
        print("hi 48 here is page: ", page)
        print("hi 49 here is group_column: ", group_column)
        print("hi 50 here is search_value: ", search_value)
        print("hi 51 here is filter: ", filter)
        if page is not None:  # Todo 20220818 this is always there unless pagination removed on UI.
            if group_column:  # generating counter without the defined queryset
                filters = Q(gathering__meet__slug__in=request.query_params.getlist("meets[]", [])).add(
                    Q(gathering__meet__assembly__division__organization=request.user.organization), Q.AND)
                print("hi 56 in if group_column")
                if start:
                    filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
                if finish:
                    filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)

                if gatherings:
                    filters.add(Q(gathering__in=gatherings), Q.AND)

                if characters:  # attendance UI always send characters but roaster UI never send characters
                    filters.add(Q(character__slug__in=characters), Q.AND)

                if isinstance(search_value, str):
                    filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
                                 |
                                 Q(attending__attendee__infos__icontains=search_value)
                                 |
                                 Q(gathering__display_name__icontains=search_value)
                                 |
                                 Q(infos__icontains=search_value)), Q.AND)

                counters = Attendance.objects.filter(filters).values(group_column).order_by(group_column).annotate(count=Count('*'))  # Count(group_column) won't count null values
                print("hi 70 here is counters: ", counters)
                return Response(Utility.group_count(group_column, counters))
            print("hi 80 Not in group_column")
            serializer = self.get_serializer(page, many=True)
            # print("hi 77 here is  serializer.data: ", serializer.data)
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
