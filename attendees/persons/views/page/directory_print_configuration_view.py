import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import ListView

from attendees.users.authorization import RouteGuard

logger = logging.getLogger(__name__)


class DirectoryPrintConfigurationView(LoginRequiredMixin, RouteGuard, ListView):
    queryset = []
    template_name = "persons/directory_print_configuration_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'pdf_url': '/persons/directory_report/',
            'organization_direct_meet': self.request.user.organization.infos.get("settings", {}).get("default_directory_meet")
        })
        return context

    def render_to_response(self, context, **kwargs):
        return render(self.request, self.get_template_names()[0], context)


directory_print_configuration_view = DirectoryPrintConfigurationView.as_view()
