from time import sleep
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class AttendingmeetEnvelopesListView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/attendingmeet_envelopes_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        show_paused = self.request.GET.get("showPaused")
        families = FolkService.folk_addresses_in_participations(
            meet_slug=self.request.GET.get("meet"),
            user_organization=self.request.user.organization,
            show_paused=show_paused,
            division_slugs=self.request.GET.getlist('divisions', []),
        ) if self.request.user.privileged() else []

        context.update({
            'report_titles': self.request.GET.get('reportTitle', '').split('\n'),
            'report_dates': self.request.GET.get('reportDate', '').split('\n'),
            'meet_slug': self.request.GET.get('meet', ''),
            'families': families,
            'attendee_url': '/persons/attendee/',
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


attendingmeet_envelopes_list_view = AttendingmeetEnvelopesListView.as_view()
