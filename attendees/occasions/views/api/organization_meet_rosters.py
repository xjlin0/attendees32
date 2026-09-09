import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.persons.services import AttendingService
from attendees.occasions.serializers.roster_serializer import RosterResponseSerializer


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetRostersViewSet(viewsets.ViewSet):
    """
    API endpoint that returns pivoted roster data (gatherings as columns, attendees as rows).
    """

    def list(self, request, *args, **kwargs):
        current_user_organization = request.user.organization
        meet_slugs = request.query_params.getlist("meets[]", [])
        start = request.query_params.get("start")
        finish = request.query_params.get("finish")

        if not meet_slugs or not start or not finish:
            return Response({"error": "meets[], start, and finish are required"}, status=400)

        # Pagination
        try:
            skip = int(request.query_params.get("skip", 0))
        except ValueError:
            skip = 0
            
        try:
            take = int(request.query_params.get("take", 40))
        except ValueError:
            take = 40

        columns, rows, total_count = AttendingService.get_roster_data(
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
            skip=skip,
            take=take
        )

        serializer = RosterResponseSerializer({
            "totalCount": total_count,
            "columns": columns,
            "rows": rows
        })

        return Response(serializer.data)
api_organization_meet_rosters_viewset = ApiOrganizationMeetRostersViewSet
