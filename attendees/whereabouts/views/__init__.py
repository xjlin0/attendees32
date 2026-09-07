from attendees.whereabouts.views.api.all_addresses import api_all_address_view_set
from attendees.whereabouts.views.api.all_states import api_all_state_view_set
from attendees.whereabouts.views.api.content_type_models import (
    content_type_list_api_view,
)
from attendees.whereabouts.views.api.datagrid_data_place import (
    api_datagrid_data_place_viewset,
)
from attendees.whereabouts.views.api.organizational_campuses import (
    api_organizational_campus_view_set,
)
from attendees.whereabouts.views.api.organizational_properties import (
    api_organizational_property_view_set,
)
from attendees.whereabouts.views.api.organizational_rooms import (
    api_organizational_room_view_set,
)
from attendees.whereabouts.views.api.organizational_suites import (
    api_organizational_suite_view_set,
)
from attendees.whereabouts.views.api.user_divisions import api_user_division_viewset
from attendees.whereabouts.views.api.user_organizations import (
    api_user_organization_viewset,
)
from attendees.whereabouts.views.api.user_places import api_user_place_view_set
from attendees.whereabouts.views.api.update_spatial import api_update_spatial_view
from attendees.whereabouts.views.api.nearest_neighbors import api_nearest_neighbors_view

__all__ = [
    "api_all_address_view_set",
    "api_all_state_view_set",
    "api_datagrid_data_place_viewset",
    "api_user_division_viewset",
    "api_user_place_view_set",
    "api_user_organization_viewset",
    "api_organizational_campus_view_set",
    "api_organizational_property_view_set",
    "api_organizational_suite_view_set",
    "api_organizational_room_view_set",
    "content_type_list_api_view",
    "api_update_spatial_view",
    "api_nearest_neighbors_view",
]
