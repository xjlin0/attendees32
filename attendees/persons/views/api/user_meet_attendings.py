import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.persons.serializers import AttendingSerializer
from attendees.persons.services import AttendingService


@method_decorator([login_required], name="dispatch")
class ApiUserMeetAttendingsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Attending to be viewed or edited.
    """

    serializer_class = AttendingSerializer

    def get_queryset(self):
        """
        :permission: this API is only for coworkers/organizers, ordinary participants should get nothing from this API
        :query: Find all gatherings of the current user, then list all attendings of the found gatherings.
                So if the current user didn't participate(attending), no info will be shown
        :return: all Attendings with participating meets(group) and character(role)
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        if current_user_organization:
            user_attended_gathering_ids = current_user.attendee.attendings.values_list(
                "gathering__id", flat=True
            ).distinct()
            return AttendingService.by_organization_meets_gatherings(
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                user_attended_gathering_ids=user_attended_gathering_ids,
                user_organization_slug=current_user_organization.slug,
            )  # didn't filter by registration start/finish within the selected time period

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_user_meet_attendings_viewset = ApiUserMeetAttendingsViewSet
