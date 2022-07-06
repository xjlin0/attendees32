import ast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework import viewsets

from attendees.persons.models import Relation
from attendees.persons.serializers import RelationSerializer
from attendees.persons.services import AttendeeService


class ApiAllRelationsViewsSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Relation(Role) to be viewed or edited. It's public and not org limited.
    """

    serializer_class = RelationSerializer

    def get_queryset(self):
        relation_id = self.request.query_params.get("relation_id")
        filters_list_string = self.request.query_params.get("filter", "[]")
        filters_list = ast.literal_eval(
            filters_list_string
        )  # copied from ApiDatagridDataAttendeesViewSet

        if relation_id:
            return Relation.objects.filter(pk=relation_id)
        else:
            init_query = Q(is_removed=False)
            final_query = init_query.add(
                AttendeeService.filter_parser(filters_list, None, self.request.user),
                Q.AND,
            )
            return Relation.objects.filter(final_query).exclude(pk=0).order_by("display_order")  # pk 0 is for code use


api_all_relations_viewset = ApiAllRelationsViewsSet
