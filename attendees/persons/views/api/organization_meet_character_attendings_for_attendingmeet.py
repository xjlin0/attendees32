import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.persons.models import Utility, Attending
from attendees.persons.serializers.attending_minimal_serializer import AttendingMinimalSerializer
from attendees.persons.services import AttendingMeetService


class ApiOrganizationMeetCharacterAttendingsViewSetForAttendingMeet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    Todo 20220514: replace LoginRequiredMixin with SpyGuard and needed seeds json
    Todo 20220514: make API returns only current users attendinmeets if not admin
    """

    serializer_class = AttendingMinimalSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, None)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, None))

    def get_queryset(self):
        current_user = self.request.user
        current_user_organization = current_user.organization

        if current_user_organization:
            pk = self.kwargs.get("pk")
            search_value = self.request.query_params.get("searchValue")
            search_expression = self.request.query_params.get("searchExpr")
            search_operation = self.request.query_params.get("searchOperation")
            group_string = self.request.query_params.get(
                "group",
            )  # [{"selector":"meet","desc":false,"isExpanded":false}] if grouping
            orderby_list = json.loads(
                self.request.query_params.get(
                    "sort",
                    '[{"selector":"meet","desc":false},{"selector":"start","desc":false}]',
                )  # default selector of meet is for AttendingMeet queries
            )  # order_by('meet','start')
            # Todo: add group column to orderby_list
            if pk:
                filters = Q(meets__assembly__division__organization=current_user_organization).add(Q(pk=pk), Q.AND)
                if not current_user.can_see_all_organizational_meets_attendees():
                    filters.add((Q(attendee__in=current_user.attendee.scheduling_attendees())
                                 |
                                 Q(registration__registrant=current_user.attendee)), Q.AND)

                return Attending.objects.filter(filters).distinct()

            else:
                if group_string:
                    groups = json.loads(group_string)
                    orderby_list.insert(
                        0, {"selector": groups[0]["selector"], "desc": groups[0]["desc"]}
                    )

                return Attending.objects.filter(
                    pk__in=AttendingMeetService.by_organization_meet_characters(
                                current_user=self.request.user,
                                meet_slugs=self.request.query_params.getlist("meets[]", []),
                                character_slugs=self.request.query_params.getlist("characters[]", []),
                                start=self.request.query_params.get("start"),
                                finish=self.request.query_params.get("finish"),
                                orderbys=orderby_list,
                                search_value=search_value,
                                search_expression=search_expression,
                                search_operation=search_operation,
                                filter=self.request.query_params.get("filter"),
                            ).values_list('attending').order_by()
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_character_attendings_viewset_for_attendingmeet = ApiOrganizationMeetCharacterAttendingsViewSetForAttendingMeet
