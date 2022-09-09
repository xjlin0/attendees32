import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, Value
from django.db.models.functions import Concat
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.models import Assembly
from attendees.occasions.serializers.assembly_serializer import AssemblySerializer


class ApiUserAssemblyViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Division to be viewed or edited.
    """

    serializer_class = AssemblySerializer

    def get_queryset(self):
        if self.request.user.organization:
            search_value = self.request.query_params.get("searchValue")
            search_expression = self.request.query_params.get("searchExpr")
            search_operation = self.request.query_params.get("searchOperation")
            extra_filter = Q(division__organization=self.request.user.organization)

            if search_value and search_expression == 'display_name' and search_operation == 'contains':
                extra_filter.add(Q(display_name__icontains=search_value), Q.AND)

            return Assembly.objects.annotate(
                division_assembly_name=Concat(
                    F("division__display_name"), Value(": "), "display_name"
                ),
            ).filter(extra_filter)

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Has your account assigned an organization?"
            )


api_user_assembly_viewset = ApiUserAssemblyViewSet
