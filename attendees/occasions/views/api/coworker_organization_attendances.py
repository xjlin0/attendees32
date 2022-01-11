import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import AttendanceSerializer
from attendees.occasions.services import AttendanceService


@method_decorator([login_required], name="dispatch")
class ApiCoworkerOrganizationAttendancesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Attendances to be viewed or edited.
    """

    serializer_class = AttendanceSerializer

    def get_queryset(self):
        """
        :permission: this API is only for coworker or organization.
                     Ordinary participants should not get any info from this API.
        :query: Find all gatherings of all Attendances of the current user, query everyone's
                Attendances in the found gatherings, so all coworker's Attendances in the
                current user participated gatherings will also show up.
        :return:  Attendances
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        gathering_ids = (
            None
            if current_user.can_see_all_organizational_meets_attendees
            else current_user.attendee.attendings.values_list(
                "gathering__id", flat=True
            )
            .distinct()
            .order_by()
        )
        if current_user_organization:
            return AttendanceService.by_organization_meets_gatherings_intervals(
                organization_slug=current_user_organization.slug,
                gathering_ids=gathering_ids,
                meet_slugs=self.request.query_params.getlist("meets[]", []),
                gathering_start=self.request.query_params.get("start", None),
                gathering_finish=self.request.query_params.get("finish", None),
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_coworker_organization_attendances_viewset = (
    ApiCoworkerOrganizationAttendancesViewSet
)
