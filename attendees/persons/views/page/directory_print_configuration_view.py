import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.users.authorization import RouteGuard
from attendees.whereabouts.models import Division

logger = logging.getLogger(__name__)


@method_decorator([login_required], name='dispatch')
class DirectoryPrintConfigurationView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_print_configuration_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'pdf_url': '/persons/directory_report/',
            'organization_direct_meet': self.request.user.organization.infos.get("settings", {}).get("default_directory_meet"),
            "divisions": Division.objects.filter(
                        organization=self.request.user.attendee.division.organization if hasattr(self.request.user, 'attendee') else self.request.user.organization,
                    ).values("id", "display_name"),
        })
        return context

    def render_to_response(self, context, **kwargs):
        return render(self.request, self.get_template_names()[0], context)


directory_print_configuration_view = DirectoryPrintConfigurationView.as_view()
