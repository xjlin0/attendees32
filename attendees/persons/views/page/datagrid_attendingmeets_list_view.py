import logging, json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService

logger = logging.getLogger(__name__)


@method_decorator([login_required], name='dispatch')
class DatagridAttendingMeetListView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/datagrid_attendingmeets_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "grade_converter": json.dumps(self.request.user.organization.infos.get('grade_converter', []) if self.request.user.organization else []),
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "attendingmeets_endpoint": "/persons/api/organization_meet_character_attendingmeets/",
                "attendings_endpoint": "/persons/api/organization_meet_character_attendings_for_attendingmeet/",
                "characters_endpoint": "/occasions/api/organization_characters/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "teams_endpoint": "/occasions/api/organization_meet_teams/",
                "categories_endpoint": "/persons/api/all_categories/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.is_ajax():
            pass

        else:
            return render(self.request, self.get_template_names()[0], context)


datagrid_attendingmeets_list_view = (
    DatagridAttendingMeetListView.as_view()
)
