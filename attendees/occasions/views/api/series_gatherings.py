from urllib import parse

import pytz
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.models import Meet
from attendees.occasions.serializers import BatchGatheringsSerializer

from attendees.occasions.services.gathering_service import GatheringService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class SeriesGatheringsViewSet(RouteGuard, viewsets.ViewSet):
    """
    API endpoint that allows batch creation of gatherings.
    """

    serializer_class = BatchGatheringsSerializer  # Required for the Browsable API renderer to have a nice form.

    def create(self, request):
        organization = request.user.organization
        meet = get_object_or_404(
            Meet,
            slug=request.data["meet_slug"],
            assembly__division__organization=organization,
        )
        tzname = (
            request.COOKIES.get("timezone")
            or meet.infos["default_time_zone"]
            or organization.infos["default_time_zone"]
            or settings.CLIENT_DEFAULT_TIME_ZONE
        )
        results = GatheringService.batch_create(
            begin=request.data.get('begin'),
            end=request.data.get('end'),
            meet_slug=request.data.get('meet_slug'),
            duration=request.data.get('duration'),
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
        )
        return Response(results)


series_gatherings_viewset = SeriesGatheringsViewSet
