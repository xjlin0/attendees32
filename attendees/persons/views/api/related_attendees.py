import ast

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.viewsets import ModelViewSet

from attendees.persons.models import Attendee
from attendees.persons.serializers import AttendeeMinimalSerializer
from attendees.persons.services import AttendeeService
from attendees.users.authorization.route_guard import SpyGuard


@method_decorator([login_required], name='dispatch')
class ApiRelatedAttendeesViewSet(SpyGuard, ModelViewSet):  # from GenericAPIView
    """
    API endpoint that allows single attendee to be viewed or edited.
    """

    serializer_class = AttendeeMinimalSerializer

    def get_queryset(self):
        """
        Return all related attendees by the attendee id in headers (key: X-TARGET-ATTENDEE-ID)
        When passing any attendee id as pk, it will return that attendee if current user is admin,
        but if the current user is NOT admin, it will only return that attendee only if the requested
        attendee were related.

        """
        current_user = (
            self.request.user
        )  # Todo 20210523: guard this API so only admin or scheduler can call it.
        target_attendee = get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )
        querying_attendee_id = self.kwargs.get("pk")
        # priority = self.request.query_params.get('priority')
        filters_list_string = self.request.query_params.get("filter", "[]")
        filters_list = ast.literal_eval(
            filters_list_string
        )  # copied from ApiDatagridDataAttendeesViewSet

        return AttendeeService.find_related_ones(
            current_user=current_user,
            target_attendee=target_attendee,
            querying_attendee_id=querying_attendee_id,
            filters_list=filters_list,
            # priority=priority,
        )


api_related_attendees_viewset = ApiRelatedAttendeesViewSet
