from urllib import parse

import pytz
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

from attendees.occasions.models import Meet
from attendees.occasions.serializers import BatchGatheringsSerializer

from attendees.occasions.services.gathering_service import GatheringService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class SeriesGatheringsViewSet(RouteGuard, viewsets.ViewSet):
    """
    API endpoint that allows batch creation of gatherings.

    IMPORTANT: Timezone is determined solely by meet.infos['default_time_zone'] since users can be anywhere
    User cookie timezone is ignored to ensure data consistency across manual and automated operations.
    """

    serializer_class = BatchGatheringsSerializer  # Required for the Browsable API renderer to have a nice form.

    def create(self, request):
        organization = request.user.organization
        meet = get_object_or_404(
            Meet,
            slug=request.data["meet_slug"],
            assembly__division__organization=organization,
        )

        # Validate meet has default_time_zone configured - critical for data consistency
        if not meet.infos.get("default_time_zone"):
            return Response({
                "success": False,
                "error": (
                    f"Meet '{meet.slug}' must have 'default_time_zone' configured in infos. "
                    f"Please configure meet.infos['default_time_zone'] (e.g., 'America/Los_Angeles') "
                    f"to prevent timezone ambiguity and data duplication."
                ),
                "meet_slug": meet.slug,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Use meet's canonical timezone - ignore user cookie for data consistency
        tzname = meet.infos["default_time_zone"]

        results = GatheringService.batch_create(
            begin=request.data.get('begin'),
            end=request.data.get('end'),
            meet_slug=request.data.get('meet_slug'),
            duration=request.data.get('duration'),
            meet=meet,
            user_time_zone=pytz.timezone(tzname),  # Parameter name kept for backwards compatibility
        )
        return Response(results)


series_gatherings_viewset = SeriesGatheringsViewSet
