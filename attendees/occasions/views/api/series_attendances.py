from urllib import parse

import pytz
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.models import Meet
from attendees.occasions.serializers import BatchAttendancesSerializer

from attendees.occasions.services import AttendanceService
from attendees.users.authorization import RouteGuard


class SeriesAttendancesViewSet(LoginRequiredMixin, RouteGuard, viewsets.ViewSet):
    """
    API endpoint that allows batch creation of gatherings.
    """

    serializer_class = BatchAttendancesSerializer  # Required for the Browsable API renderer to have a nice form.

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
        results = AttendanceService.batch_create(
            **request.data,
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
        )
        return Response(results)


series_attendances_viewset = SeriesAttendancesViewSet
