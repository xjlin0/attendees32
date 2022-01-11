import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, F, When
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.models import Meet
from attendees.occasions.serializers.meet import MeetSerializer
from attendees.persons.models import Attendee, AttendingMeet


class ApiUserAssemblyMeetsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Meet to be viewed or edited.
    """

    serializer_class = MeetSerializer

    def get_queryset(self):
        """
        Todo: this endpoint is used by datagrid_attendee_update_view page (with params).
              Do check if the editor and the editing target relations and permissions
        :return:
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        target_attendee = get_object_or_404(
            Attendee,
            pk=self.request.META.get(
                "HTTP_X_TARGET_ATTENDEE_ID", current_user.attendee_uuid_str()
            ),
        )

        if current_user_organization:
            filters = {"assembly__division__organization": current_user_organization}
            assemblies = self.request.query_params.getlist("assemblies[]")
            if assemblies:
                filters["assembly__in"] = assemblies
            return (
                Meet.objects.filter(**filters)
                .annotate(
                    assembly_name=F("assembly__display_name"),
                )
                .order_by(
                    Case(
                        When(
                            id__in=AttendingMeet.objects.filter(
                                attending__attendee=target_attendee
                            )
                            .values_list("meet")
                            .distinct(),
                            then=0,
                        ),
                        default=1,
                    ),
                )
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_user_assembly_meets_viewset = ApiUserAssemblyMeetsViewSet
