import time
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.serializers import CharacterSerializer
from attendees.occasions.services import CharacterService
from attendees.persons.models import Attendee


@method_decorator([login_required], name="dispatch")
class ApiUserAssemblyCharactersViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Character to be viewed or edited.
    """

    serializer_class = CharacterSerializer

    def get_queryset(self):
        """
        Todo: this endpoint is used by datagrid_coworker_organization_attendances (no params) and
              datagrid_attendee_update_view page (with params). Do check if the editor and
              the editing target relations and permissions
        :return:
        """
        current_user = self.request.user
        current_user_organization = current_user.organization
        target_attendee = get_object_or_404(  # for DRF UI
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID", self.request.user.attendee_uuid_str())
        ) if settings.DEBUG else get_object_or_404(
            Attendee, pk=self.request.META.get("HTTP_X_TARGET_ATTENDEE_ID")
        )

        if current_user_organization:
            return CharacterService.by_organization_assemblies(
                organization=current_user_organization,
                assemblies=self.request.query_params.getlist("assemblies[]"),
                target_attendee=target_attendee,
                search_value=self.request.query_params.get("searchValue"),
                search_operation=self.request.query_params.get("searchOperation"),
                search_column=self.request.query_params.get("searchExpr")
            )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have you registered any events of the organization?"
            )


api_user_assembly_characters_viewset = ApiUserAssemblyCharactersViewSet
