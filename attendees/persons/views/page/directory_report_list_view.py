import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard

logger = logging.getLogger(__name__)


class DirectoryReportListView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_report_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        index_row_per_page = int(self.request.GET.get("indexRowPerPage", '26'))
        page_breaks_before_index = int(self.request.GET.get("pageBreaksBeforeIndex", '2'))
        indexes, families = FolkService.families_in_directory(index_row_per_page)
        context.update({
            'directory_header': self.request.GET.get('directoryHeader', ''),
            'index_header': self.request.GET.get('indexHeader', ''),
            'families': families,
            'indexes': indexes,
            'index_page_breaks': range(page_breaks_before_index),
            'empty_image_link': f'{settings.STATIC_URL}images/empty.png'
        })
        return context

    def render_to_response(self, context, **kwargs):
        return render(self.request, self.get_template_names()[0], context)


directory_report_list_view = DirectoryReportListView.as_view()
