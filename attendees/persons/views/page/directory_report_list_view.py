import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic.list import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard

logger = logging.getLogger(__name__)


class DirectoryReportListView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_report_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'families': FolkService.families_in_directory(),
        })
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.is_ajax():
            pass

        else:
            return render(self.request, self.get_template_names()[0], context)


directory_report_list_view = DirectoryReportListView.as_view()
