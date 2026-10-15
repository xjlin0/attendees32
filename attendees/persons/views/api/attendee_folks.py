import time

from django.db import models
from django.db.models import Case, F, OuterRef, Prefetch, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from attendees.persons.models import Attendee, Category, Folk, FolkAttendee
from attendees.persons.serializers import FolkSerializer
from attendees.persons.services import FolkService, AttendingMeetService
from attendees.users.authorization.drf_guards import DrfSpyGuard
from attendees.whereabouts.models import Place


class ApiAttendeeFolksViewsSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Folks(families) of an Attendee (in header) to be viewed or edited.
    """
    permission_classes = [IsAuthenticated, DrfSpyGuard]

    serializer_class = FolkSerializer

    def get_queryset(self):
        folk_id = self.kwargs.get("pk")
        category = get_object_or_404(
            Category,
            pk=self.request.query_params.get("categoryId", Attendee.FAMILY_CATEGORY),
        )
        current_user = self.request.user
        target_attendee_id = self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        attendee = Attendee.objects.filter(pk=target_attendee_id).first() if target_attendee_id != 'new' else (current_user.attendee if current_user.can_see_all_organizational_meets_attendees() else None)
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        extra_filter = Q(category=category)
        extra_filter.add(Q(division__organization=current_user.organization), Q.AND)

        if search_value and search_expression == 'display_name' and search_operation == 'contains':
            extra_filter.add((Q(attendees__infos__icontains=search_value)
                              |
                              Q(display_name__icontains=search_value)), Q.AND)

        if folk_id and folk_id != 'new':
            extra_filter.add(Q(pk=folk_id), Q.AND)

        places_prefetch = Prefetch(
            "places",
            queryset=Place.objects.filter(is_removed=False).select_related(
                "content_type", "address__locality__state"
            ),
        )

        if current_user.privileged_to_edit(attendee and attendee.id):
            if folk_id:
                return Folk.objects.filter(extra_filter).prefetch_related(places_prefetch, "attendees")
            else:
                role_subquery = Subquery(
                    FolkAttendee.objects.filter(
                        folk=OuterRef("pk"),
                        attendee=attendee,
                        is_removed=False,
                    ).values("role_id")[:1],
                    output_field=models.IntegerField(),
                )
                return (
                    Folk.objects.filter(extra_filter)
                    .annotate(
                        role_order=Coalesce(role_subquery, Value(9999), output_field=models.IntegerField()),
                    )
                    .annotate(
                        relative_order=Case(
                            When(role_order__lt=9999, then=Value(1)),
                            default=Value(10),
                            output_field=models.IntegerField(),
                        )
                    )
                    .order_by("relative_order", "role_order", "display_order")
                    .prefetch_related(places_prefetch, "attendees")
                )
        else:
            return (
                attendee.folks.filter(extra_filter).prefetch_related(places_prefetch, "attendees")
                if attendee
                else Folk.objects.none()
            )

    def perform_create(
        self, serializer
    ):  # SpyGuard ensured requester & target_attendee belongs to the same org.
        serializer.save()
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        target_attendee.save(update_fields=['modified'])

    def perform_update(self, serializer):  # Todo 20220706 respond for joining and families count
        instance = serializer.save()
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        print_directory = self.request.META.get("HTTP_X_PRINT_DIRECTORY") and instance.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, instance.attendees.all(), directory_meet_id, print_directory)
        target_attendee.save(update_fields=['modified'])

    def perform_destroy(self, instance):
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        if self.request.user.privileged_to_edit(target_attendee.id):
            FolkService.destroy_with_associations(instance, target_attendee)
            target_attendee.save(update_fields=['modified'])

        else:
            time.sleep(2)
            raise PermissionDenied(
                detail=f"Not allowed to delete {instance.__class__.__name__}"
            )


api_attendee_folks_viewset = ApiAttendeeFolksViewsSet
