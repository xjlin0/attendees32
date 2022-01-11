import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from attendees.whereabouts.models import Organization

from attendees.whereabouts.serializers import OrganizationSerializer


class ApiUserOrganizationViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Division to be viewed or edited.
    """
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        if self.request.user.organization:
            # organization_id = self.request.query_params.get('pk')
            return Organization.objects.filter(pk=self.request.user.organization.id)

        else:
            time.sleep(2)
            raise AuthenticationFailed(detail='Have your account assigned an organization?')


api_user_organization_viewset = ApiUserOrganizationViewSet
