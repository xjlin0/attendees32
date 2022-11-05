from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService


@method_decorator([login_required], name='dispatch')
class LocationTimelineListView(RouteGuard, ListView):
    queryset = []
    template_name = "occasions/location_timeline_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_organization_calendar = self.request.user.organization.calendar_relations.filter(distinction='source').first()
        context.update(
            {
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "content_type_models_endpoint": "/whereabouts/api/content_type_models/",
                "calendars_endpoint": "/occasions/api/organization_calendars/",
                "organization_default_calendar": user_organization_calendar and user_organization_calendar.id or 0,
                "occurrences_endpoint": "/occasions/api/organization_occurrences/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.is_ajax():
            pass

        else:
            return render(self.request, self.get_template_names()[0], context)


location_timeline_list_view = LocationTimelineListView.as_view()
