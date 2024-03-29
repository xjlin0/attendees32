import logging
from time import sleep
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard
from attendees.whereabouts.models import Division

logger = logging.getLogger(__name__)


@method_decorator([login_required], name='dispatch')
class DirectoryReportListView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_report_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        division_ids = self.request.GET.getlist('divisionSelector', [])
        index_row_per_page = int(self.request.GET.get("indexRowPerPage", '26'))
        page_breaks_before_index = int(self.request.GET.get("pageBreaksBeforeIndex", '2'))
        user_org_settings = self.request.user.organization.infos.get("settings", {})
        indexes, families = FolkService.families_in_directory(
            directory_meet_id=user_org_settings.get('default_directory_meet'),
            member_meet_id=user_org_settings.get('default_member_meet'),
            row_limit=index_row_per_page,
            targeting_attendee_id=None,
            divisions=Division.objects.filter(pk__in=division_ids, organization=self.request.user.organization),
        ) if self.request.user.privileged() else ([], [])  # parenthesis are required
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
        if self.request.user.privileged():  # data_admins and counselor
            return render(self.request, self.get_template_names()[0], context)
        else:
            sleep(2)
            return HttpResponse(
                "Based on your organization's settings, you do not have permissions to visit this!",
                status=403,
            )


directory_report_list_view = DirectoryReportListView.as_view()
