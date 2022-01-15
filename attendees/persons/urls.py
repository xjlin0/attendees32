from django.urls import include, path
from rest_framework import routers

from attendees.persons.views import (  # api_attendee_relationships_viewset,
    api_all_categories_viewset,
    api_all_relations_viewset,
    api_all_registrations_viewset,
    api_categorized_pasts_viewset,
    api_assembly_meet_attendings_viewset,
    api_attendee_folks_viewset,
    api_data_attendings_viewset,
    api_datagrid_data_attendees_viewset,
    api_datagrid_data_attendee_viewset,
    api_related_attendees_viewset,
    api_datagrid_data_attendingmeet_viewset,
    api_assembly_meet_attendees_viewset,
    api_datagrid_data_folkattendees_viewset,
    # api_attendee_relationships_viewset,
    datagrid_assembly_all_attendings_list_view,
    attendees_list_view,
    datagrid_assembly_data_attendings_list_view,
    attendee_update_view,
    api_attendee_attendings_viewset,
    api_user_meet_attendings_viewset,
    api_family_organization_attendings_viewset,
)

app_name = "persons"

router = routers.DefaultRouter()  # (trailing_slash=False)
router.register(
    "api/datagrid_data_attendees",
    api_datagrid_data_attendees_viewset,
    basename="attendee",
)
router.register(
    "api/(?P<division_slug>.+)/(?P<assembly_slug>.+)/assembly_meet_attendings",
    api_assembly_meet_attendings_viewset,
    basename="attending",
)
router.register(
    "api/attendee_attendings",
    api_attendee_attendings_viewset,
    basename="attending",
)
router.register(
    "api/(?P<division_slug>.+)/(?P<assembly_slug>.+)/data_attendings",
    api_data_attendings_viewset,
    basename="attending",
)
router.register(
    "api/(?P<division_slug>.+)/(?P<assembly_slug>.+)/assembly_meet_attendees",
    api_assembly_meet_attendees_viewset,
    basename="attendee",
)
router.register(
    "api/user_meet_attendings",
    api_user_meet_attendings_viewset,
    basename="attending",
)
router.register(
    "api/family_organization_attendings",
    api_family_organization_attendings_viewset,
    basename="attending",
)
router.register(
    "api/datagrid_data_attendee",
    api_datagrid_data_attendee_viewset,
    basename="attendee",
)
router.register(
    "api/datagrid_data_attendingmeet",
    api_datagrid_data_attendingmeet_viewset,
    basename="attendingmeet",
)
router.register(
    "api/datagrid_data_familyattendees",
    api_datagrid_data_folkattendees_viewset,
    basename="folkattendee",
)
router.register(
    "api/all_relations",
    api_all_relations_viewset,
    basename="relation",
)
router.register(
    "api/attendee_relationships",
    api_datagrid_data_folkattendees_viewset,  # api_attendee_relationships_viewset,
    basename="folkattendee",
)  # Todo 20211125: seperate viewset instead of sending category params
router.register(
    "api/categorized_pasts",
    api_categorized_pasts_viewset,
    basename="past",
)
router.register(
    "api/all_categories",
    api_all_categories_viewset,
    basename="category",
)
router.register(
    "api/all_registrations",
    api_all_registrations_viewset,
    basename="registration",
)
router.register(
    "api/related_attendees",
    api_related_attendees_viewset,
    basename="attendee",
)
router.register(
    "api/attendee_families",
    api_attendee_folks_viewset,
    basename="family",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<slug:division_slug>/<slug:assembly_slug>/datagrid_assembly_all_attendings/",
        view=datagrid_assembly_all_attendings_list_view,
        name="datagrid_assembly_all_attendings",
    ),
    path(
        "attendees/",
        view=attendees_list_view,
        name="attendees_list_view",
    ),
    path(
        "<slug:division_slug>/<slug:assembly_slug>/datagrid_assembly_data_attendings/",
        view=datagrid_assembly_data_attendings_list_view,
        name="datagrid_assembly_data_attendings",
    ),
    path(
        "attendee/self",
        view=attendee_update_view,
        name="attendee_update_self",  # null attendee_id will be replaced by request.user's attendee_id
    ),
    path(
        "attendee/new",
        kwargs={"attendee_id": "new", "show_create_attendee": False},
        view=attendee_update_view,
        name="attendee_create_view",  # for create attendee permission
    ),
    path(
        "attendee/<str:attendee_id>",
        view=attendee_update_view,
        name="attendee_update_view",
    ),
]
