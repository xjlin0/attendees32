from json import dumps
from time import sleep

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import render
from django.views.generic import UpdateView

from attendees.persons.models import Attendee, Folk
from attendees.users.authorization import RouteAndSpyGuard
from attendees.users.models import Menu
from attendees.utils.view_helpers import get_object_or_delayed_403
from attendees.whereabouts.models import Division


class AttendeeUpdateView(LoginRequiredMixin, RouteAndSpyGuard, UpdateView):
    model = Attendee
    fields = "__all__"
    template_name = "persons/attendee_update_view.html"

    def get_object(self, queryset=None):
        # queryset = self.get_queryset() if queryset is None else queryset
        if queryset:
            return get_object_or_delayed_403(queryset)
        else:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        targeting_attendee_id = self.kwargs.get(
            "attendee_id", self.request.user.attendee_uuid_str()
        )  # if more logic needed when create new, a new view will be better
        show_create_attendee = self.kwargs.get(
            "show_create_attendee", Menu.user_can_create_attendee(self.request.user)
        )
        context.update(
            {
                "attendee_contenttype_id": ContentType.objects.get_for_model(
                    Attendee
                ).id,
                "teams_endpoint": "/occasions/api/organization_meet_teams/",
                "folk_contenttype_id": ContentType.objects.get_for_model(Folk).id,
                "empty_image_link": f"{settings.STATIC_URL}images/empty.png",
                "show_create_attendee": show_create_attendee,
                "characters_endpoint": "/occasions/api/user_assembly_characters/",
                "meets_endpoint": "/occasions/api/user_assembly_meets/",
                "attendingmeets_endpoint": "/persons/api/datagrid_data_attendingmeet/",
                "assemblies_endpoint": "/occasions/api/user_assemblies/",
                "divisions_endpoint": "/whereabouts/api/user_divisions/",
                "addresses_endpoint": "/whereabouts/api/all_addresses/",
                "states_endpoint": "/whereabouts/api/all_states/",
                "relations_endpoint": "/persons/api/all_relations/",
                "pasts_endpoint": "/persons/api/categorized_pasts/",
                "categories_endpoint": "/persons/api/all_categories/",
                "registrations_endpoint": "/persons/api/all_registrations/",
                "relationships_endpoint": "/persons/api/attendee_relationships/",
                "related_attendees_endpoint": "/persons/api/related_attendees/",  # may not only be families
                "attendee_families_endpoint": "/persons/api/attendee_families/",
                "attendings_endpoint": "/persons/api/attendee_attendings/",
                "family_attendees_endpoint": "/persons/api/datagrid_data_familyattendees/",
                "family_category_id": Attendee.FAMILY_CATEGORY,
                "targeting_attendee_id": targeting_attendee_id,
                "divisions": dumps(
                    list(
                        Division.objects.filter(
                            organization=self.request.user.attendee.division.organization
                        ).values("id", "display_name")
                    )
                ),  # to avoid simultaneous AJAX calls
                "attendee_search": "/persons/api/datagrid_data_attendees/",
                "attendee_urn": "/persons/attendee/",
            }
        )
        return context

    def render_to_response(
        self, context, **kwargs
    ):  # attendee_id "new" only happened in attendee_create_view checked by RouteAndSpyGuard
        if context[
            "targeting_attendee_id"
        ] == "new" or self.request.user.attendee.under_same_org_with(
            context["targeting_attendee_id"]
        ):
            if self.request.is_ajax():
                pass

            else:
                context.update(
                    {"attendee_endpoint": "/persons/api/datagrid_data_attendee/"}
                )
                return render(self.request, self.get_template_names()[0], context)
        else:
            sleep(2)
            raise Http404("Have you registered any events of the organization?")


attendee_update_view = AttendeeUpdateView.as_view()
