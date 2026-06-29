from django.urls import include, path
from rest_framework import routers

from attendees.whereabouts.views import (
    api_all_address_view_set,
    api_all_state_view_set,
    api_datagrid_data_place_viewset,
    api_organizational_campus_view_set,
    api_organizational_property_view_set,
    api_organizational_room_view_set,
    api_organizational_suite_view_set,
    api_user_division_viewset,
    api_user_organization_viewset,
    api_user_place_view_set,
    content_type_list_api_view,
    api_update_spatial_view,
    api_nearest_neighbors_view,
)

app_name = "whereabouts"

router = routers.DefaultRouter()
router.register(
    "api/user_divisions",
    api_user_division_viewset,
    basename="user_division",
)
router.register(
    "api/user_places",
    api_user_place_view_set,
    basename="user_place",
)
router.register(
    "api/datagrid_data_place",
    api_datagrid_data_place_viewset,
    basename="datagrid_place",
)
router.register(
    "api/all_addresses",
    api_all_address_view_set,
    basename="all_address",
)
router.register(
    "api/all_states",
    api_all_state_view_set,
    basename="all_state",
)
router.register(
    "api/user_organizations",
    api_user_organization_viewset,
    basename="user_organization",
)
router.register(
    "api/organizational_campuses",
    api_organizational_campus_view_set,
    basename="organizational_campus",
)
router.register(
    "api/organizational_properties",
    api_organizational_property_view_set,
    basename="organizational_property",
)
router.register(
    "api/organizational_suites",
    api_organizational_suite_view_set,
    basename="organizational_suite",
)
router.register(
    "api/organizational_rooms",
    api_organizational_room_view_set,
    basename="organizational_room",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "api/content_type_models/",
        content_type_list_api_view.as_view(),
        name="content_type",
    ),
    path(
        "api/content_type_models/<str:pk>/",
        content_type_list_api_view.as_view(),
        name="content_type",
    ),
    path(
        "api/update_spatial_for/<str:pk>/",
        api_update_spatial_view,
        name="update_spatial",
    ),
    path(
        "api/nearest_neighbors_for/<str:pk>/",
        api_nearest_neighbors_view,
        name="nearest_neighbors",
    ),
]
