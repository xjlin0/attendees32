from urllib import parse

import pytz
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.models import Meet
from attendees.occasions.serializers import BatchAttendancesSerializer

from attendees.occasions.services import AttendanceService, GatheringService
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
        gathering_results = GatheringService.batch_create(
            **request.data,
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
        )
        attendance_results = AttendanceService.batch_create(
            begin=request.data['begin'],
            end=request.data['end'],
            meet_slug=request.data['meet_slug'],
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
        )
        attendance_results['gathering_generation_success'] = gathering_results['success']
        attendance_results['gathering_created'] = gathering_results['number_created']
        return Response(attendance_results)


series_attendances_viewset = SeriesAttendancesViewSet
