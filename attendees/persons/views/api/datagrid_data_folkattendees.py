from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets

from attendees.persons.models import Attendee, FolkAttendee
from attendees.persons.serializers import FolkAttendeeSerializer
from attendees.persons.services import AttendingMeetService
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiDatagridDataFolkAttendeesViewsSet(SpyGuard, viewsets.ModelViewSet
):
    """
    API endpoint that allows FamiliesAttendees of a single Attendee in headers to be viewed or edited.
    For example, if Alice, Bob & Charlie are in a family, passing Alice's attendee id in headers (key:
    X-TARGET-ATTENDEE-ID) will return all 3 FamilyAttendee objects of Alice, Bob & Charlie. Also,
    attaching Bob's FamilyAttendee id at the end of the endpoint will return Bob's FamilyAttendee only.

    Note: If Dick is not in the family, passing Dick's attendee id in headers plus Bob's FamilyAttendee
    id at the end of the endpoint will return nothing.
    """

    serializer_class = FolkAttendeeSerializer

    def get_queryset(self):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        target_folkattendee_id = self.kwargs.get("pk")
        category = self.request.query_params.get("categoryId")

        if target_folkattendee_id:
            return FolkAttendee.objects.filter(pk=target_folkattendee_id)

        else:
            filters = Q(
                folk__in=target_attendee.folks.filter(folkattendee__is_removed=False)
            )

            if category:
                filters = filters & Q(folk__category=category)

            if not self.request.user.privileged():
                expire_filter = Q(finish__isnull=True).add(
                    Q(finish__gte=datetime.now(timezone.utc)), Q.OR
                )
                filters = filters & expire_filter

            return (
                FolkAttendee.objects.filter(filters)
                .exclude(
                    role=Attendee.HIDDEN_ROLE,
                )
                .order_by(
                    "folk",
                    "folk__display_order",
                    "display_order",
                    "role__display_order",
                )
            )

    def perform_update(self, serializer):  # Todo 20220706 respond for joining and families count
        instance = serializer.save()
        print_directory = instance.folk.infos.get('print_directory') and instance.folk.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance.attendee], directory_meet_id, print_directory)

    def perform_create(self, serializer):
        instance = serializer.save()
        print_directory = instance.folk.infos.get('print_directory') and instance.folk.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, [instance.attendee], directory_meet_id, print_directory)


api_datagrid_data_folkattendees_viewset = ApiDatagridDataFolkAttendeesViewsSet
