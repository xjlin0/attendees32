import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import GatheringSerializer
from attendees.occasions.services import GatheringService


@method_decorator([login_required], name="dispatch")
class ApiFamilyOrganizationGatheringsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = GatheringSerializer

    def get_queryset(self):
        """
        :permission: this API is only for authenticated users (participants, coworker or organization).
                     Anonymous users should not get any info from this API.
        :query: Find all gatherings of all Attendances of the current user and their kid/care receiver, so all
                their "family" attending gatherings (including not joined characters) will show up.
        :return:  all Gatherings of the logged in user and their kids/care receivers.
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        if current_user_organization:
            # Todo: probably need to check if the meets belongs to the organization?
            return GatheringService.by_family_meets(
                user=current_user,
                meet_slugs=self.request.query_params.getlist("meets[]", []),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_family_organization_gatherings_viewset = ApiFamilyOrganizationGatheringsViewSet
