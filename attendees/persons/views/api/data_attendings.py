import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.persons.serializers import AttendingSerializer
from attendees.persons.services import AttendingService


@method_decorator([login_required], name="dispatch")
class ApiDataAttendingsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Attending to be viewed or edited.
    """

    serializer_class = AttendingSerializer

    def get_queryset(self):
        if self.request.user.belongs_to_divisions_of([self.kwargs["division_slug"]]):
            # Todo: probably also need to check if the assembly belongs to the division
            return AttendingService.by_assembly_meet_characters(
                assembly_slug=self.kwargs["assembly_slug"],
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                character_slugs=self.request.query_params.getlist("characters[]", []),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_data_attendings_viewset = ApiDataAttendingsViewSet
