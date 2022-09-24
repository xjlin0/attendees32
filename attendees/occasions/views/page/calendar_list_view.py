from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.users.authorization import RouteGuard
from attendees.users.services import MenuService


@method_decorator([login_required], name='dispatch')
class CalendarListView(RouteGuard, ListView):
    queryset = []
    template_name = "occasions/calendar_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "user_can_write": MenuService.is_user_allowed_to_write(self.request),
                "content_type_models_endpoint": "/whereabouts/api/content_type_models/",
                # "gatherings_endpoint": "/occasions/api/organization_team_gatherings/",
                # "series_gatherings_endpoint": "/occasions/api/series_gatherings/",
                # "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                # "meets_endpoint_by_id": "/occasions/api/user_assembly_meets/",
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.is_ajax():
            pass

        else:
            return render(self.request, self.get_template_names()[0], context)

    # def test(self):
    #     meet.event_relations.first().event.get_occurrences(
    #         datetime(2021,8,1,tzinfo=pytz.utc),
    #         datetime(2021,8,20,tzinfo=pytz.utc)
    #     )
    #     return None


calendar_list_view = CalendarListView.as_view()
