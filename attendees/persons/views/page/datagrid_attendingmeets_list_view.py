import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard

logger = logging.getLogger(__name__)


class DatagridAttendingMeetListView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/datagrid_attendingmeets_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "attendingmeets_endpoint": "/persons/api/organization_meet_character_attendingmeets/",
                "attendings_endpoint": "/persons/api/organization_meet_character_attendings/",
                "characters_endpoint": "/occasions/api/organization_characters/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "teams_endpoint": "/occasions/api/organization_meet_teams/",
                "categories_endpoint" : "/persons/api/all_categories/",
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
