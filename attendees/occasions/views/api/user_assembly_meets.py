import time

from django.contrib.auth.decorators import login_required
from django.db.models import Case, F, When
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed

from attendees.occasions.models import Meet
from attendees.occasions.serializers.meet import MeetSerializer
from attendees.persons.models import Attendee, AttendingMeet


@method_decorator([login_required], name="dispatch")
class ApiUserAssemblyMeetsViewSet(viewsets.ModelViewSet):
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
                "HTTP_X_TARGET_ATTENDEE_ID", current_user.attendee_uuid_str() or None
            ),
        )
        # Todo 20200530: filter meets by user's group like Meet.objects.filter(infos__allowed_groups__0__in=['children_coworker', 'hi']) if infos = {'allowed_groups': ['children_coworker', 'data_organizer']}
        if hasattr(current_user, 'attendee') and current_user_organization:
            filters = {"assembly__division__organization": current_user_organization}
            model = self.request.query_params.get("model")
            assemblies = self.request.query_params.getlist("assemblies[]")
            search_value = self.request.query_params.get("searchValue")
            search_operation = self.request.query_params.get("searchOperation")

            if search_value and search_operation == 'contains':
                search_column = self.request.query_params.get("searchExpr")
                filters[f'{search_column}__icontains'] = search_value

            if assemblies:
                filters["assembly__in"] = assemblies

            if model:
                filters["infos__allowed_models__regex"] = fr'({model})'

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
                detail="Have you registered any events of the organization? Does your user associate with an attendee?"
            )


api_user_assembly_meets_viewset = ApiUserAssemblyMeetsViewSet
