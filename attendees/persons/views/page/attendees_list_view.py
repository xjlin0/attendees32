from json import dumps

from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView

from attendees.occasions.models import Meet
from attendees.persons.models import Utility
from attendees.users.authorization import RouteGuard
from attendees.users.models import Menu

# import logging

# logger = logging.getLogger(__name__)


@method_decorator([login_required], name='dispatch')
class AttendeesListView(RouteGuard, ListView):
    queryset = []
    template_name = "persons/attendees_list_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Todo include user divisions and meets slugs in context
        family_attendances_menu = Menu.objects.filter(
            url_name="datagrid_user_organization_attendances"
        ).first()
        available_meets = (
            Meet.objects.filter(
                (Q(finish__isnull=True) | Q(finish__gt=Utility.now_with_timezone())),
                assembly__division__organization=self.request.user.organization,
            )
            .annotate(
                assembly_name=F("assembly__display_name"),
            )
            .order_by("assembly_name")
            .values("id", "slug", "display_name", "assembly_name")
        )  # Todo 20210711 only coworkers can see all Meet, general users should only see what they attended
        allowed_to_create_attendee = Menu.user_can_create_attendee(self.request.user)
        context.update(
            {
                "family_attendances_urn": family_attendances_menu.urn
                if family_attendances_menu
                else None,
                "available_meets_json": dumps(list(available_meets)),
                "allowed_to_create_attendee": allowed_to_create_attendee,
                "create_attendee_urn": "/persons/attendee/new",
            }
        )
        return context

    def render_to_response(
        self, context, **kwargs
    ):  # view only provides empty tables, it's API that needs to return valid data
        # if self.request.user.belongs_to_divisions_of([context['current_division_slug']]):
        if self.request.is_ajax():
            pass

        else:
            # chosen_character_slugs = self.request.GET.getlist('characters', [])
            # context.update({'chosen_character_slugs': chosen_character_slugs})
            context.update({"divisions_endpoint": "/whereabouts/api/user_divisions/"})
            # context.update({'teams_endpoint': (f"/occasions/api/{context['current_division_slug']}"
            #                                    f"/{context['current_assembly_slug']}/assembly_meet_teams/"}))
            # context.update({'attendees_endpoint': (f"/persons/api/{context['current_division_slug']}"
            #                                        f"/{context['current_assembly_slug']}/assembly_meet_attendees/"}))
            context.update({"attendee_urn": "/persons/attendee/"})
            # context.update({'gatherings_endpoint': (f"/occasions/api/{context['current_division_slug']}"
            #                                         f"/{context['current_assembly_slug']}/assembly_meet_gatherings/")})
            # context.update({'characters_endpoint': (f"/occasions/api/{context['current_division_slug']}"
            #                                         f"/{context['current_assembly_slug']}/assembly_meet_characters/")})
            # context.update({'attendings_endpoint': (f"/persons/api/{context['current_division_slug']}"
            #                                         f"/{context['current_assembly_slug']}/data_attendings/")})
            # context.update({'attendances_endpoint': (f"/occasions/api/{context['current_division_slug']}"
            #                                        f"/{context['current_assembly_slug']}/assembly_meet_attendances/")})
            return render(self.request, self.get_template_names()[0], context)
        # else:
        #     time.sleep(2)
        #     raise Http404('Have you registered any events of the organization?')

    # def get_attendances(self, args):
    #     return []

    # def get_partial_template(self):
    #     return ''


attendees_list_view = AttendeesListView.as_view()
