from functools import partial
from itertools import count
from time import sleep
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class AttendingmeetReportListView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/attendingmeet_report_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        families = FolkService.families_in_participations(
            meet_slug=self.request.GET.get("meet"),
            user_organization=self.request.user.organization,
            skip_paused=self.request.GET.get("skip_paused"),
            division_slugs=self.request.GET.getlist('divisions', []),
        ) if self.request.user.privileged() else []

        context.update({
            'report_title': self.request.GET.get('reportTitle', ''),
            'report_date': self.request.GET.get('reportDate', ''),
            'meet_slug': self.request.GET.get('meet', ''),
            'families': families,
            'counter': partial(next, count(1)),
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


attendingmeet_report_list_view = AttendingmeetReportListView.as_view()
