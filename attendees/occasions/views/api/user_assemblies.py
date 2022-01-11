import time

from django.contrib.auth.decorators import login_required
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.models import Assembly
from attendees.occasions.serializers.assembly_serializer import AssemblySerializer


@method_decorator([login_required], name="dispatch")
class ApiUserAssemblyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Division to be viewed or edited.
    """

    serializer_class = AssemblySerializer

    def get_queryset(self):
        if self.request.user.organization:
            return Assembly.objects.annotate(
                division_assembly_name=Concat(
                    F("division__display_name"), Value(": "), "display_name"
                ),
            ).filter(
                division__organization=self.request.user.organization,
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


api_user_assembly_viewset = ApiUserAssemblyViewSet
