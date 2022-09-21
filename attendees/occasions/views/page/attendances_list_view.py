from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService


@method_decorator([login_required], name='dispatch')
class AttendancesListView(RouteGuard, ListView):
    queryset = []
    template_name = "occasions/attendances_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
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
        if self.request.is_ajax():
            pass

        else:
            return render(self.request, self.get_template_names()[0], context)


attendances_list_view = AttendancesListView.as_view()
