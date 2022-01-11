import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.persons.serializers import AttendeeSerializer
from attendees.persons.services import AttendeeService


@method_decorator([login_required], name="dispatch")
class ApiAssemblyMeetAttendeesSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    """

    serializer_class = AttendeeSerializer

    def get_queryset(self):
        if self.request.user.belongs_to_divisions_of([self.kwargs["division_slug"]]):
            return AttendeeService.by_assembly_meets(
                assembly_slug=self.kwargs["assembly_slug"],
                meet_slugs=self.request.query_params.getlist("meets[]", []),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_assembly_meet_attendees_viewset = ApiAssemblyMeetAttendeesSet
