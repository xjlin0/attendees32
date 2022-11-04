import logging
import time

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.authorization import PeekOther
from attendees.users.services import MenuService

logger = logging.getLogger(__name__)


@method_decorator([login_required], name='dispatch')
class DatagridUserOrganizationAttendancesListView(RouteGuard, ListView):
    queryset = []
    template_name = 'occasions/datagrid_user_organization_attendances.html'

    def get_context_data(self, **kwargs):
        attendee_id = self.kwargs.get("attendee_id")
        current_user = self.request.user
        attendee = PeekOther.get_attendee_or_self(current_user, attendee_id)
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "attendee_name": attendee.display_label,
                "attendee_id": attendee.id,
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "categories_endpoint": "/persons/api/all_categories/",
                "gatherings_endpoint": "/occasions/api/organization_team_gatherings/",
                "attendances_endpoint": "/occasions/api/organization_meet_character_attendances/",
                "attendings_endpoint": "/persons/api/organization_meet_character_attendings_for_attendance/",
                "characters_endpoint": "/occasions/api/organization_characters/",
                "series_attendances_endpoint": "/occasions/api/series_attendances/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "meets_endpoint_by_id": "/occasions/api/user_assembly_meets/",
                "teams_endpoint": "/occasions/api/organization_meet_teams/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.user.organization:
            if self.request.is_ajax():
                pass

            else:
                return render(self.request, self.get_template_names()[0], context)
        else:
            time.sleep(2)
            raise Http404("Have you registered any events of the organization?")


#
#     # def get_attendances(self, args):
#     #     return []
#
#     # def get_partial_template(self):
#     #     return ''


datagrid_user_organization_attendances_list_view = (
    DatagridUserOrganizationAttendancesListView.as_view()
)
