import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from django.conf import settings
from attendees.persons.models import Attendee, Attending
from attendees.persons.serializers.attending_minimal_serializer import (
    AttendingMinimalSerializer,
)
from attendees.persons.services import AttendingService


class ApiAttendeeAttendingsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Attending of a target attendee to be viewed or edited.
    Target attendee is specified by http header x-target-attendee-id or current user's attendee
    """

    serializer_class = AttendingMinimalSerializer

    def get_queryset(self):
        target_attendee_id = self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        target_attendee = get_object_or_404(  # for DRF UI
            Attendee, pk=target_attendee_id or self.request.user.attendee_uuid_str()
        ) if settings.DEBUG else get_object_or_404(
            Attendee, pk=target_attendee_id
        )
        current_user_organization = self.request.user.organization
        is_self = (
            current_user_organization
            and self.request.user.attendee
            and self.request.user.attendee == target_attendee
        )
        is_privileged = current_user_organization and self.request.user.privileged_to_edit(target_attendee_id)
        if target_attendee and (
            is_self
            or is_privileged
            or self.request.user.attendee.can_schedule_attendee(target_attendee.id)
        ):
            attending_id = self.kwargs.get("pk")
            qs = Attending.objects.filter(
                attendee=target_attendee,
                attendee__division__organization=current_user_organization,
            )  # With correct data this query will only work if current user's org is the same as targeting attendee's

            if attending_id:
                return qs.filter(pk=attending_id)
            else:
                return qs

        #     return AttendingService.by_assembly_meet_characters(
        #         assembly_slug=self.kwargs['assembly_slug'],
        #         meet_slugs=self.request.query_params.getlist('meets[]', []),
        #         character_slugs=self.request.query_params.getlist('characters[]', []),
        #     )
        # return Attending.objects.select_related().prefetch_related().filter(
        #     meets__slug__in=meet_slugs,
        #     attendingmeet__character__slug__in=character_slugs,
        #     meets__assembly__slug=assembly_slug,
        # ).distinct()

        else:
            time.sleep(2)
            raise PermissionDenied(detail="Are you data admin or counselor?")

    def perform_create(self, serializer):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if target_attendee.under_same_org_with(
            self.request.user.attendee and self.request.user.attendee.id
        ):
            serializer.save(attendee=target_attendee)

        else:
            time.sleep(2)
            raise PermissionDenied(
                detail="Can't create attending across different organization"
            )

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):
            AttendingService.destroy_with_associations(instance)

        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_attendee_attendings_viewset = ApiAttendeeAttendingsViewSet
