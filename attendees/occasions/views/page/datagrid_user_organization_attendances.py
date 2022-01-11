import logging
import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.views.generic.list import ListView

from attendees.occasions.models import Meet
from attendees.users.authorization import PeekOther

logger = logging.getLogger(__name__)


class DatagridUserOrganizationAttendancesListView(LoginRequiredMixin, ListView):
    queryset = []
    template_name = 'occasions/datagrid_user_organization_attendances.html'

    def get_context_data(self, **kwargs):
        attendee_id = self.kwargs.get("attendee_id")
        current_user = self.request.user
        user_organization = current_user.organization
        attendee = PeekOther.get_attendee_or_self(current_user, attendee_id)
        context = super().get_context_data(**kwargs)

        available_meets = (
            Meet.objects.filter(
                Q(attendings__attendee=attendee),
                # |
                # Q(attendings__attendee__in=attendee.related_ones.filter(
                #     from_attendee__scheduler=True,
                # ))
            )
            .order_by(
                "display_name",
            )
            .distinct()
        )  # get all user's and user care receivers' joined meets, no time limit on the first load

        context.update(
            {
                "attendee_name": attendee.display_label,
                "current_organization_slug": user_organization.slug,
                "available_meets": available_meets,
            }
        )
        return context

    def render_to_response(self, context, **kwargs):
        if self.request.user.organization:
            if self.request.is_ajax():
                pass

            else:
                # chosen_character_slugs = self.request.GET.getlist('characters', [])
                # context.update({'chosen_character_slugs': chosen_character_slugs})
                context.update(
                    {"teams_endpoint": "/occasions/api/organization_meet_teams/"}
                )
                context.update(
                    {
                        "gatherings_endpoint": "/occasions/api/family_organization_gatherings/"
                    }
                )
                context.update(
                    {
                        "characters_endpoint": "/occasions/api/family_organization_characters/"
                    }
                )
                context.update(
                    {
                        "attendings_endpoint": "/persons/api/family_organization_attendings/"
                    }
                )
                context.update(
                    {
                        "attendances_endpoint": "/occasions/api/family_organization_attendances/"
                    }
                )
                return render(self.request, self.get_template_names()[0], context)
        else:
            time.sleep(2)
            raise Http404("Have you registered any events of the organization?")


#
#     # def get_attendances(self, args):
#     #     return []
#
#     # def get_partial_template(self):
#     #     return ''


datagrid_user_organization_attendances_list_view = (
    DatagridUserOrganizationAttendancesListView.as_view()
)
