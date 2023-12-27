import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.expressions import F
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.viewsets import ModelViewSet

from attendees.occasions.models import Attendance
from attendees.persons.models import Attendee, AttendingMeet, Utility
from attendees.persons.serializers import AttendingMeetEtcSerializer
from attendees.users.authorization.route_guard import SpyGuard


class ApiDatagridDataAttendingMeetViewSet(
    LoginRequiredMixin, SpyGuard, ModelViewSet
):  # from GenericAPIView
    """
    API endpoint that allows AttendingMeet & Meet to be viewed or edited.
    """

    serializer_class = AttendingMeetEtcSerializer

    def get_queryset(self):
        """
        Return AttendingMeet of the target attendee sent in header, can be further specified by pk in url param
        """
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        querying_attendingmeet_id = self.kwargs.get("pk")
        filters = {
            'attending__attendee': target_attendee,
            'meet__assembly__division__organization': self.request.user.organization,
        }
        if querying_attendingmeet_id:
            filters['pk'] = querying_attendingmeet_id
        qs = AttendingMeet.objects.annotate(
            assembly=F("meet__assembly"),
            meet__assembly__display_order=F('meet__assembly__display_order'),
        ).filter(**filters)

        return qs.order_by(
            'meet__assembly__display_order',
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.attending.attendee.save(update_fields=['modified'])

    def perform_update(self, serializer):
        instance = serializer.save()
        instance.attending.attendee.save(update_fields=['modified'])

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(  # intentionally forbid user delete him/herself
            target_attendee.id
        ):
            Attendance.objects.filter(
                gathering__meet=instance.meet,
                gathering__start__gte=Utility.now_with_timezone(),
                attending=instance.attending
            ).delete()  # delete only future attendance
            instance.delete()
            target_attendee.save(update_fields=['modified'])
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_datagrid_data_attendingmeet_viewset = ApiDatagridDataAttendingMeetViewSet
