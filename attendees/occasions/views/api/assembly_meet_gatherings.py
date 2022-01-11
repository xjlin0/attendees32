import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import GatheringSerializer
from attendees.occasions.services import GatheringService


@method_decorator([login_required], name="dispatch")
class ApiAssemblyMeetGatheringsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = GatheringSerializer

    def get_queryset(self):
        if self.request.user.belongs_to_divisions_of([self.kwargs["division_slug"]]):
            # Todo: probably need to check if the assembly belongs to the division
            return GatheringService.by_assembly_meets(
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                assembly_slug=self.kwargs["assembly_slug"],
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_assembly_meet_gatherings_viewset = ApiAssemblyMeetGatheringsViewSet
