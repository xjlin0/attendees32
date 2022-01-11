import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import TeamSerializer
from attendees.occasions.services import TeamService


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetTeamViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = TeamSerializer

    def get_queryset(self):
        current_user_organization = self.request.user.organization
        if current_user_organization:
            # Todo: probably need to check if the meets belongs to the organization?
            return TeamService.by_organization_meets(
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                organization_slug=current_user_organization.slug,
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_team_viewset = ApiOrganizationMeetTeamViewSet
