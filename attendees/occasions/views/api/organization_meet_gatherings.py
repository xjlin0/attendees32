import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.aggregates import Count
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.models import Gathering
from attendees.occasions.serializers import GatheringSerializer
from attendees.occasions.services import GatheringService
from attendees.persons.models import Utility


class ApiOrganizationMeetGatheringsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = GatheringSerializer

    def list(self, request, *args, **kwargs):
        """
        Todo 20220610: This is grouping AFTER queryset, thus the count of items for each group is incorrect after paging.
        Todo 20220610: To make the count correct when grouping, the count needs to be query and grouped at db level
        """
        group_string = request.query_params.get(
            "group", '[{}]'
        )  # [{"selector":"meet","desc":false,"isExpanded":false}] if grouping
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        group_column = json.loads(group_string)[0].get('selector')
        current_user_organization = request.user.organization
        meet_slugs = request.query_params.getlist("meets[]", [])

        if page is not None:
            if group_column:
                counters = Gathering.objects.filter(
                    meet__slug__in=meet_slugs,
                    meet__assembly__division__organization=current_user_organization,
                ).values(group_column).order_by(group_column).annotate(count=Count(group_column))
                return Response(Utility.group_count(group_column, counters))

            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, group_column)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, group_column))

    def get_queryset(self):
        current_user = self.request.user
        current_user_organization = self.request.user.organization

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
                extra_filters = {
                    'pk': pk,
                    'meet__assembly__division__organization': current_user_organization,
                }
                if not current_user.can_see_all_organizational_meets_attendees():
                    extra_filters['attendings__attendee'] = current_user.attendee

                return Gathering.objects.filter(**extra_filters)

            else:
                if group_string:
                    groups = json.loads(group_string)
                    orderby_list.insert(
                        0, {"selector": groups[0]["selector"], "desc": groups[0]["desc"]}
                    )

                return GatheringService.by_organization_meets(
                    current_user=self.request.user,
                    meet_slugs=self.request.query_params.getlist("meets[]", []),
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


api_organization_meet_gatherings_viewset = ApiOrganizationMeetGatheringsViewSet
