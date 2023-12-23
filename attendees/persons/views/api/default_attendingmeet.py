import time

from django.contrib.auth.decorators import login_required
from django.db.models.expressions import F
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.exceptions import PermissionDenied
from rest_framework.viewsets import ModelViewSet

from attendees.occasions.models import Attendance
from attendees.persons.models import Attendee, AttendingMeet, Utility
from attendees.persons.serializers import AttendingmeetDefaultSerializer
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiDefaultAttendingmeetsViewSet(SpyGuard, ModelViewSet):  # from GenericAPIView
    """
    API endpoint that allows AttendingMeet to be created/modified by the default character and attending
    """

    serializer_class = AttendingmeetDefaultSerializer

    def get_queryset(self):
        """
        Return AttendingMeet of the target attendee sent in header, can be further specified by pk in url param
        """
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        print("hi 31 ApiDefaultAttendingMeetViewSet#get_queryset, self.request.query_params", self.request.query_params)
        querying_attendingmeet_id = self.kwargs.get("pk")
        filters = {"attending__attendee": target_attendee}
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
        print("hi 46 ApiDefaultAttendingMeetViewSet#perform_create, serializer", serializer)
        instance = serializer.save()
        instance.attending.attendee.save(update_fields=['modified'])

    def perform_update(self, serializer):
        print("hi 51 ApiDefaultAttendingMeetViewSet#perform_update, serializer", serializer)
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


api_default_attendingmeets_viewset = ApiDefaultAttendingmeetsViewSet
