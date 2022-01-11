import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import AttendanceSerializer
from attendees.occasions.services import AttendanceService


@method_decorator([login_required], name="dispatch")
class ApiAssemblyMeetAttendancesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Attendances to be viewed or edited.
    """

    serializer_class = AttendanceSerializer

    def get_queryset(self):
        if self.request.user.belongs_to_divisions_of([self.kwargs["division_slug"]]):
            # Todo: probably need to check if the assembly belongs to the division?
            return AttendanceService.by_assembly_meets_characters_gathering_intervals(
                assembly_slug=self.kwargs["assembly_slug"],
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                gathering_start=self.request.query_params.get("start", None),
                gathering_finish=self.request.query_params.get("finish", None),
                character_slugs=self.request.query_params.getlist("characters[]", []),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_assembly_meet_attendances_viewset = ApiAssemblyMeetAttendancesViewSet
