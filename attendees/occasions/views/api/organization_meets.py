import time

from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from attendees.occasions.models import Meet
from attendees.occasions.serializers.meet import MeetSerializer
from attendees.persons.models import Utility


@method_decorator([login_required], name="dispatch")
class OrganizationMeetsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows all/grouped Meet in current user's organization filtered by date to be viewed or edited.
    Todo 20210711 only coworkers/organizers can see all Meets, general users should only see what they attended
    Todo 20210815 if limiting by meet's shown_audience, non-coworker assigned to non-public meets won't show
    """

    serializer_class = MeetSerializer

    def list(self, request, *args, **kwargs):
        grouping = request.query_params.get("grouping")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, grouping)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, grouping))

    def get_queryset(self):
        current_user_organization = self.request.user.organization
        model = self.request.query_params.get("model")
        user_groups = self.request.user.groups.values_list('name', flat=True)

        if current_user_organization:
            start = self.request.query_params.get("start")
            finish = self.request.query_params.get("finish")
            search_value = self.request.query_params.get("searchValue")
            search_expression = self.request.query_params.get("searchExpr")
            search_operation = self.request.query_params.get("searchOperation")
            assemblies = self.request.query_params.getlist("assemblies[]")
            extra_filter = Q(assembly__division__organization=current_user_organization)

            if user_groups:
                extra_filter.add(Q(infos__allowed_groups__regex=fr"({'|'.join([name for name in user_groups])})"), Q.AND)

            if model:
                extra_filter.add(Q(infos__allowed_models__regex=fr'({model})'), Q.AND)

            if assemblies:
                extra_filter.add(Q(assembly__in=assemblies), Q.AND)

            if search_value and search_operation == 'contains':  # only contains supported now
                terms = {f'{search_expression}__icontains': search_value}
                extra_filter.add(Q(**terms), Q.AND)

            if start:
                extra_filter.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)

            if finish:
                extra_filter.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)

            return (
                Meet.objects.filter(extra_filter)
                .annotate(
                    assembly_name=F("assembly__display_name"),
                )
                .order_by("assembly_name")
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


organization_meets_viewset = OrganizationMeetsViewSet
