import logging
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic.list import ListView
from weasyprint.text.fonts import FontConfiguration

from attendees.persons.models import Utility
from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard

from weasyprint import HTML

logger = logging.getLogger(__name__)


class DirectoryReportListView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_report_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'families': FolkService.families_in_directory(),
            "empty_image_link": f"{settings.STATIC_URL}images/empty.png"
        })
        return context

    def render_to_response(self, context, **kwargs):
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = "inline; filename=directory.pdf".format(
            date=Utility.now_with_timezone().strftime('%Y-%m-%d'),
            name='directory',
        )
        print("hi 37 here is APPS_DIR: ", settings.APPS_DIR)
        print("hi 38 here is ROOT_DIR: ", settings.ROOT_DIR)
        # domain = f"{self.request.scheme}://{settings.BASE_URI or self.request.get_host()}"
        html = render_to_string("persons/directory_report_list_view.html", {
            'families': FolkService.families_in_directory(),
            "empty_image_link": f"/static/images/empty.png",
            # 'image_base_url': settings.WEASYPRINT_BASEURL,
        })

        font_config = FontConfiguration()
        HTML(string=html, base_url=".").write_pdf(response, font_config=font_config)
        return response


directory_report_list_view = DirectoryReportListView.as_view()
