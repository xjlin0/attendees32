from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from attendees.persons.services import FolkService
from attendees.users.authorization import RouteGuard


@method_decorator([login_required], name='dispatch')
class PersonDirectoryPreview(RouteGuard, ListView):
    queryset = []
    template_name = "persons/person_directory_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_org_settings = self.request.user.organization.infos.get("settings", {})
        indexes, families = FolkService.families_in_directory(
            directory_meet_id=user_org_settings.get('default_directory_meet'),
            member_meet_id=user_org_settings.get('default_member_meet'),
            targeting_attendee_id=self.kwargs.get("attendee_id"),
        )
        context.update({
            'families': families,
            'attendee_urn': '/persons/attendee/',
            'empty_image_link': f'{settings.STATIC_URL}images/empty.png'
        })
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.is_ajax():
            html = render_to_string(self.get_template_names()[0], context)
            return HttpResponse(html)
        else:
            return render(self.request, self.get_template_names()[0], context)


person_directory_preview = PersonDirectoryPreview.as_view()
