from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService
from attendees.whereabouts.services import DivisionService


@method_decorator([login_required], name='dispatch')
class RostersListView(RouteGuard, ListView):
    queryset = []
    template_name = "occasions/rosters_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "grade_converter": self.request.user.organization.infos.get('grade_converter', []) if (self.request.user and getattr(self.request.user, "organization", None) and isinstance(self.request.user.organization.infos, dict)) else [],
                "divisions": list(DivisionService.by_organization(self.request.user.organization.slug).values("id", "display_name")) if (self.request.user and getattr(self.request.user, "organization", None)) else [],
                "divisions_endpoint": "/whereabouts/api/user_divisions/",
                "gatherings_endpoint": "/occasions/api/organization_team_gatherings/",
                "attendances_endpoint": "/occasions/api/organization_meet_character_attendances/",
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "categories_endpoint": "/persons/api/all_categories/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "rosters_endpoint": "/occasions/api/organization_meet_rosters/",
                "attendingmeets_endpoint": "/persons/api/datagrid_data_attendingmeet/",
                "attendings_endpoint": "/persons/api/organization_meet_character_attendings_for_attendingmeet/",
                "characters_endpoint": "/occasions/api/organization_characters/",
                "teams_endpoint": "/occasions/api/organization_meet_teams/",
                "search_attendees_endpoint": "/persons/api/search_attendees_for_roster/",
                "fast_onboard_endpoint": "/persons/api/fast_onboard_attendee/",
                "relations_endpoint": "/persons/api/all_relations/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.accepts("text/html"):
            return render(self.request, self.get_template_names()[0], context)


rosters_list_view = RostersListView.as_view()
