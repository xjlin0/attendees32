import time
from itertools import groupby
from operator import itemgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.models import Gathering
from attendees.occasions.serializers import GatheringSerializer
from attendees.occasions.services import GatheringService


class ApiOrganizationMeetGatheringsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = GatheringSerializer

    def transform_result(self, data, group_string):
        if group_string:
            results = []
            groups = json.loads(group_string)
            for c_title, items in groupby(data, itemgetter(groups[0]["selector"])):
                groped_data = list(items)
                results.append({"key": c_title, "items": groped_data})
            return results
        else:
            return data

    def list(self, request, *args, **kwargs):
        group_string = request.query_params.get(
            "group"
        )  # [{"selector":"meet","desc":false,"isExpanded":false}] if grouping
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                self.transform_result(serializer.data, group_string)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(self.transform_result(serializer.data, group_string))

    def get_queryset(self):
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
            # Todo: add group colume to orderby_list
            if pk:
                return Gathering.objects.filter(
                    pk=pk,
                    meet__assembly__division__organization=current_user_organization,
                )

            else:
                if group_string:
                    groups = json.loads(group_string)
                    orderby_list.insert(
                        0, {"selector": groups[0]["selector"], "desc": False}
                    )

                return GatheringService.by_organization_meets(
                    current_user=self.request.user,
                    meet_slugs=self.request.query_params.getlist("meets[]", []),
                    start=self.request.query_params.get("start"),
                    finish=self.request.query_params.get("finish"),
                    orderbys=orderby_list,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_gatherings_viewset = ApiOrganizationMeetGatheringsViewSet
