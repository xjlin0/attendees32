from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService


@method_decorator([login_required], name='dispatch')
class RostersListView(RouteGuard, ListView):
    queryset = []
    template_name = "occasions/rosters_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "categories_endpoint": "/persons/api/all_categories/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "rosters_endpoint": "/occasions/api/organization_meet_rosters/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.accepts("text/html"):
            return render(self.request, self.get_template_names()[0], context)


rosters_list_view = RostersListView.as_view()
