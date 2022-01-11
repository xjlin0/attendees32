from datetime import datetime, timezone

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from attendees.persons.models import Attendee, FolkAttendee
from attendees.persons.serializers import FolkAttendeeSerializer
from attendees.users.authorization.route_guard import SpyGuard


class ApiDatagridDataFolkAttendeesViewsSet(
    LoginRequiredMixin, SpyGuard, viewsets.ModelViewSet
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
        category = self.request.query_params.get("category")

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


api_datagrid_data_folkattendees_viewset = ApiDatagridDataFolkAttendeesViewsSet
