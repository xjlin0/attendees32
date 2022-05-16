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

    # def retrieve(self, request, *args, **kwargs):
    #     attendingmeet_id = self.kwargs.get('pk')
    #     print("hi 23 hre is attendingmeet_id: ")
    #     print(attendingmeet_id)
    #     attendee = AttendingMeet.objects.annotate(
    #         assembly=F('meet__assembly'),
    #         attendingmeets=JSONBAgg(
    #             Func(
    #                 Value('slug'), 'attending__meets__slug',
    #                 Value('display_name'), 'attending__meets__display_name',
    #                 function='jsonb_build_object'
    #             ),
    #         )
    #                ).filter(pk=attendingmeet_id).first()
    #     serializer = AttendingMeetEtcSerializer(attendee)
    #     return Response(serializer.data)

    def get_queryset(self):
        """
        Return AttendingMeet of the target attendee sent in header, can be further specified by pk in url param
        """
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        querying_attendingmeet_id = self.kwargs.get("pk")
        qs = AttendingMeet.objects.annotate(assembly=F("meet__assembly"),).filter(
            attending__attendee=target_attendee,
        )

        if querying_attendingmeet_id:
            return qs.filter(pk=querying_attendingmeet_id)
        else:
            return qs

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(  # intentionally forbid user delete him/herself
            target_attendee.id
        ):
            Attendance.objects.filter(
                gathering__meet=instance.meet,
                gathering__start_gte=Utility.now_with_timezone(),
                attending=instance.attending
            ).delete()  # delete only future attendance
            instance.delete()
        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_datagrid_data_attendingmeet_viewset = ApiDatagridDataAttendingMeetViewSet
