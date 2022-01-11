import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from attendees.persons.models import Attendee, Category
from attendees.persons.serializers import FolkSerializer
from attendees.persons.services import FolkService
from attendees.users.authorization.route_guard import SpyGuard


class ApiAttendeeFolksViewsSet(LoginRequiredMixin, SpyGuard, viewsets.ModelViewSet):
    """
    API endpoint that allows Folks(families) of an Attendee (in header) to be viewed or edited.
    """

    serializer_class = FolkSerializer

    def get_queryset(self):
        attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        folk_id = self.kwargs.get("pk")
        category = get_object_or_404(
            Category,
            pk=self.request.query_params.get("categoryId", Attendee.FAMILY_CATEGORY),
        )
        if folk_id:
            return attendee.folks.filter(pk=folk_id, category=category)
        else:
            return attendee.folks.filter(category=category).order_by("display_order")

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):
            FolkService.destroy_with_associations(instance, target_attendee)

        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_attendee_folks_viewset = ApiAttendeeFolksViewsSet
