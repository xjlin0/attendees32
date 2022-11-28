import time

from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Value
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from attendees.persons.models import Attendee, Category, Folk
from attendees.persons.serializers import FolkSerializer
from attendees.persons.services import FolkService, AttendingMeetService
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiAttendeeFolksViewsSet(SpyGuard, viewsets.ModelViewSet):
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
        current_user = self.request.user
        search_value = self.request.query_params.get("searchValue")
        search_expression = self.request.query_params.get("searchExpr")
        search_operation = self.request.query_params.get("searchOperation")
        extra_filter = Q(category=category)
        extra_filter.add(Q(division__organization=current_user.organization), Q.AND)

        if search_value and search_expression == 'display_name' and search_operation == 'contains':
            extra_filter.add((Q(attendees__infos__icontains=search_value)
                              |
                              Q(display_name__icontains=search_value)), Q.AND)

        if folk_id:
            extra_filter.add(Q(pk=folk_id), Q.AND)

        if current_user.privileged_to_edit(attendee.id):
            if folk_id:
                return Folk.objects.filter(extra_filter)
            else:
                attendees_folks = attendee.folks.annotate(relative_order=Value(1), role_order=F('folkattendee__role')).filter(extra_filter)
                other_folks = Folk.objects.annotate(relative_order=Value(10), role_order=Value(9999)).filter(extra_filter)
                return attendees_folks.union(other_folks).order_by('relative_order', 'role_order')
        else:
            return attendee.folks.filter(extra_filter)

    def perform_update(self, serializer):  # Todo 20220706 respond for joining and families count
        instance = serializer.save()
        print_directory = self.request.META.get("HTTP_X_PRINT_DIRECTORY") and instance.category_id == 0  # family
        directory_meet_id = self.request.user.organization.infos.get('settings', {}).get('default_directory_meet')
        AttendingMeetService.flip_attendingmeet_by_existing_attending(self.request.user, instance.attendees.all(), directory_meet_id, print_directory)

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
