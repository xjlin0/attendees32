import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.utils import json

from attendees.occasions.services import AttendanceService
from attendees.persons.models import Utility, Attending
from attendees.persons.serializers.attending_minimal_serializer import AttendingMinimalSerializer


class ApiOrganizationMeetCharacterAttendingsViewSetForAttendance(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Team to be viewed or edited.
    Todo 20220514: replace LoginRequiredMixin with SpyGuard and needed seeds json
    Todo 20220514: make API returns only current users attendinmeets if not admin
    """

    serializer_class = AttendingMinimalSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                Utility.transform_result(serializer.data, None)
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(Utility.transform_result(serializer.data, None))

    def get_queryset(self):
        current_user = self.request.user
        current_user_organization = current_user.organization

        if current_user_organization:
            pk = self.kwargs.get("pk")
            search_value = self.request.query_params.get("searchValue")
            search_expression = self.request.query_params.get("searchExpr")
            search_operation = self.request.query_params.get("searchOperation")
            orderby_list = json.loads(
                self.request.query_params.get(
                    "sort",
                    '[{"selector":"gathering.meet","desc":false},{"selector":"start","desc":false}]',
                )
            )  # order_by('meet','start')
            # Todo: add group column to orderby_list
            if pk:
                filters = Q(meets__assembly__division__organization=current_user_organization).add(Q(pk=pk), Q.AND)
                if not current_user.can_see_all_organizational_meets_attendees():
                    filters.add((Q(attendee__in=current_user.attendee.scheduling_attendees())
                                 |
                                 Q(registration__registrant=current_user.attendee)), Q.AND)

                return Attending.objects.filter(filters).distinct()

            else:  # Originally only provide what's from attendingmeet, however in the field managers just want to add anyone
                filters = Q(attendee__division__organization=current_user_organization)
                if search_value and search_operation == 'contains' and search_expression == 'attending_label':  # for searching in drop down of popup editor
                    filters.add((Q(registration__registrant__infos__icontains=search_value)
                                 |
                                 Q(attendee__infos__icontains=search_value)), Q.AND)

                return Attending.objects.filter(filters).order_by('attendee__last_name')

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_organization_meet_character_attendings_viewset_for_attendance = ApiOrganizationMeetCharacterAttendingsViewSetForAttendance
