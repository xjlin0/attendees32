import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import CharacterSerializer
from attendees.occasions.services import CharacterService


@method_decorator([login_required], name="dispatch")
class ApiAssemblyMeetCharactersViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Character to be viewed or edited.
    """

    serializer_class = CharacterSerializer

    def get_queryset(self):
        if self.request.user.belongs_to_divisions_of([self.kwargs["division_slug"]]):
            # Todo: probably need to check if the assembly belongs to the division?
            return CharacterService.by_assembly_meets(
                assembly_slug=self.kwargs["assembly_slug"],
                meet_slugs=self.request.query_params.getlist("meets[]", []),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_assembly_meet_characters_viewset = ApiAssemblyMeetCharactersViewSet
