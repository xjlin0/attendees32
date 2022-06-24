import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
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
        search_value = json.loads(self.request.query_params.get("filter", "[[null]]"))[0][-1]

        if page is not None:
            if group_column:
                filters = Q(meet__slug__in=request.query_params.getlist("meets[]", [])).add(
                    Q(meet__assembly__division__organization=request.user.organization), Q.AND)

                if search_value:
                    search_filters = Q(infos__icontains=search_value)
                    search_filters.add(Q(display_name__icontains=search_value), Q.OR)

                    for site, field in GatheringService.SITE_SEARCHING_PROPERTIES.items():
                        site_filter = {f"{field}__icontains": search_value}
                        search_filters.add(
                            (Q(site_type__model=site._meta.model_name)
                             &
                             Q(site_id__in=[str(key)  # can't use site_id__regex=r'(1|2|3)' for empty r'()'
                                            for key in site.objects.filter(**site_filter).values_list('id', flat=True)]
                               )
                             ), Q.OR)
                    filters.add(search_filters, Q.AND)

                counters = Gathering.objects.filter(filters).values(group_column).order_by(group_column).annotate(count=Count(group_column))
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
                extra_filters = Q(
                    meet__assembly__division__organization=current_user_organization
                ).add(Q(pk=pk), Q.AND)

                if not current_user.can_see_all_organizational_meets_attendees():
                    extra_filters.add((Q(attendings__attendee__in=current_user.attendee.scheduling_attendees())
                                       |
                                       Q(attendings__registration__registrant=current_user.attendee)), Q.AND)

                return Gathering.objects.filter(extra_filters)

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
