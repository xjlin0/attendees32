import time

from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.whereabouts.models import Organization
from attendees.whereabouts.serializers import OrganizationSerializer


class ApiUserOrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that returns the caller's own organization (its infos carry the
    grade_converter and settings), to a browser session or a DRF token alike.
    Read-only: the organization is edited in the admin, and letting any member
    write infos here would let them grant themselves its privilege groups.
    """

    serializer_class = OrganizationSerializer

    def get_queryset(self):
        if self.request.user.organization:
            # organization_id = self.request.query_params.get('pk')
            return Organization.objects.filter(pk=self.request.user.organization.id)

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


api_user_organization_viewset = ApiUserOrganizationViewSet
