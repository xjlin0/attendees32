import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class AttendingmeetPrintConfigurationView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/attendingmeet_print_configuration_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'pdf_url': '/persons/attendingmeet_report/',
            'envelopes_url': '/persons/attendingmeet_envelopes/',
            "meets_endpoint_by_slug": "/occasions/api/organization_meets/",
            "divisions_endpoint": "/whereabouts/api/user_divisions/",
        })
        return context

    def render_to_response(self, context, **kwargs):
        return render(self.request, self.get_template_names()[0], context)


attendingmeet_print_configuration_view = AttendingmeetPrintConfigurationView.as_view()
