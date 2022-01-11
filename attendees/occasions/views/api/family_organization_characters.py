import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import CharacterSerializer
from attendees.occasions.services import CharacterService


@method_decorator([login_required], name="dispatch")
class ApiFamilyOrganizationCharactersViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Character to be viewed.  All characters in the
    authenticated user (and kids/care receiver)'s attending meets will be shown.
    """

    serializer_class = CharacterSerializer

    def get_queryset(self):
        """
        :permission: this API is only for authenticated users (participants, coworker or organization).
                     Anonymous users should not get any info from this API.
        :query: Find all gatherings of all Attendances of the current user and their kid/care receiver, so all
                their "family" attendances gathering's characters (including not joined characters) will show up.
        :return:  all Characters of the logged in user and their kids/care receivers' gathering.
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        if current_user_organization:
            # user_assemblys = current_user.attendee.attendings.values_list('registration__assembly')
            # care_receiver_assemblys = current_user.attendee.related_ones.filter(
            #     to_attendee__relation__in=Attendee.BE_LISTED_KEYWORDS
            # ).values_list('attendings__registration__assembly')
            return CharacterService.by_family_meets_gathering_intervals(
                user=current_user,
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_family_organization_characters_viewset = ApiFamilyOrganizationCharactersViewSet
