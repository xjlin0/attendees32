from urllib import parse

import pytz
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.models import Meet
from attendees.occasions.serializers import BatchAttendancesSerializer

from attendees.occasions.services import AttendanceService, GatheringService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class SeriesAttendancesViewSet(RouteGuard, viewsets.ViewSet):
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
            begin=request.data.get('begin'),
            end=request.data.get('end'),
            meet_slug=request.data.get('meet_slug'),
            duration=request.data.get('duration'),
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
        )
        attendance_results = AttendanceService.batch_create(
            begin=request.data.get('begin'),
            end=request.data.get('end'),
            meet_slug=request.data.get('meet_slug'),
            meet=meet,
            user_time_zone=pytz.timezone(parse.unquote(tzname)),
            attendee_id=request.data.get('attendee'),
        )
        attendance_results['gathering_generation_success'] = gathering_results['success']
        attendance_results['gathering_created'] = gathering_results['number_created']
        return Response(attendance_results)


series_attendances_viewset = SeriesAttendancesViewSet
