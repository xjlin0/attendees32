import logging
import time
from json import dumps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms.models import model_to_dict
from django.http import Http404
from django.shortcuts import render
from django.views.generic.list import ListView

from attendees.occasions.models import Character, Meet
from attendees.users.authorization import RouteGuard

logger = logging.getLogger(__name__)


class DatagridAttendingMeetListView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/datagrid_attendingmeets_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                # "content_type_models_endpoint": "/whereabouts/api/content_type_models/",
                "attendingmeets_endpoint": "/persons/api/organization_meet_character_attendingmeets/",
                # "series_gatherings_endpoint": "/occasions/api/series_gatherings/",
                "characters_endpoint": "/occasions/api/organization_characters/",
                "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
                "meets_endpoint_by_id": "/occasions/api/user_assembly_meets/",
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
