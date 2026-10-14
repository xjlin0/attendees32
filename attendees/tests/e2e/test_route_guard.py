"""Which personas may open which pages.

``RouteGuard`` decides whether a login's auth groups may open a URL at all, from
the ``users.Menu`` rows the seed ships. The expected matrix is written out
longhand here, so a change to the seed's permission design shows up as a
failing test rather than a silent widening. What each page renders is tested
per page, in ``pages/``.
"""

import pytest

from attendees.tests.golden import PERSONAS
from attendees.tests.golden.constants import AssemblySlugs, DIVISION_SLUGS, MeetSlugs
from attendees.tests.e2e.helpers import ROUTE_REFUSED

pytestmark = pytest.mark.django_db


CHILDREN_COWORKER = "children_coworker"
CHILDREN_ORGANIZER = "children_organizer"
CONFERENCE_ORGANIZER = "conference_organizer"
DATA_COUNSELOR = "data_counselor"
DATA_ORGANIZER = "data_organizer"
PARTICIPANT = "organization_participant"
ROSTER_EQUIPMENTS = "roster_equipments"

EVERYONE_IN_A_MINISTRY = frozenset(
    {CHILDREN_COWORKER, CHILDREN_ORGANIZER, CONFERENCE_ORGANIZER, DATA_COUNSELOR,
     DATA_ORGANIZER}
)
EVERYONE = EVERYONE_IN_A_MINISTRY | {PARTICIPANT}


def _attendee_path(key):
    def build(golden):
        return f"/persons/attendee/{golden.attendee(key).id}"

    return build


#: ``(name, path or path-builder, groups whose members may read the page)``
#:
#: Three of these are behind ``RouteAndSpyGuard`` rather than ``RouteGuard``;
#: they refuse with a 403 page instead of the explanatory 200, and the spy half
#: adds per-person rules on top of the group rules.  ``SPY_GUARDED`` and
#: ``EXTRA_ALLOWED`` below carry those differences.
PAGES = (
    ("attendees_list_view", "/persons/attendees/", EVERYONE),
    ("attendee_update_self", "/persons/attendee/self", EVERYONE),
    ("attendee_create_view", "/persons/attendee/new", EVERYONE_IN_A_MINISTRY),
    ("attendee_update_view", _attendee_path("chen_grace"), EVERYONE_IN_A_MINISTRY),
    ("attendingmeets_list_view", "/persons/attendingmeets/", EVERYONE),
    ("directory_print_configuration_view", "/persons/directory_print_configuration/",
     frozenset({CHILDREN_COWORKER, DATA_ORGANIZER})),
    ("attendingmeet_print_configuration_view",
     "/persons/attendingmeet_print_configuration/", frozenset({DATA_ORGANIZER})),
    ("directory_report_list_view", "/persons/directory_report/",
     frozenset({CHILDREN_COWORKER, DATA_ORGANIZER})),
    ("attendingmeet_report_list_view",
     f"/persons/attendingmeet_report/?meet={MeetSlugs.DIRECTORY}",
     frozenset({DATA_ORGANIZER})),
    ("attendingmeet_envelopes_list_view",
     f"/persons/attendingmeet_envelopes/?meet={MeetSlugs.DIRECTORY}",
     frozenset({DATA_ORGANIZER})),
    ("person_directory_preview",
     lambda golden: f"/persons/directory_preview/{golden.attendee('chen_zhiming').id}",
     frozenset({CHILDREN_ORGANIZER, CONFERENCE_ORGANIZER, DATA_COUNSELOR,
                DATA_ORGANIZER})),
    ("datagrid_assembly_all_attendings",
     f"/persons/{DIVISION_SLUGS[3]}/{AssemblySlugs.JUNIOR_REGULAR}"
     "/datagrid_assembly_all_attendings/",
     frozenset({CHILDREN_COWORKER, CHILDREN_ORGANIZER})),
    ("datagrid_assembly_data_attendings",
     f"/persons/{DIVISION_SLUGS[5]}/{AssemblySlugs.CONGREGATION_DATA}"
     "/datagrid_assembly_data_attendings/",
     frozenset({DATA_ORGANIZER})),
    ("gatherings_list_view", "/occasions/gatherings/", EVERYONE),
    ("attendances_list_view", "/occasions/attendances/", EVERYONE),
    ("roster_list_view", "/occasions/roster/",
     EVERYONE_IN_A_MINISTRY | {ROSTER_EQUIPMENTS}),
    ("attendance_statistics_list_view", "/occasions/attendance_statistics/",
     frozenset({CHILDREN_ORGANIZER, CONFERENCE_ORGANIZER, DATA_COUNSELOR,
                DATA_ORGANIZER})),
    ("calendars_list_view", "/occasions/calendars/", EVERYONE),
    ("location_timeline_list_view", "/occasions/location_timeline/",
     EVERYONE_IN_A_MINISTRY),
    ("datagrid_user_organization_attendances",
     "/occasions/datagrid_user_organization_attendances/",
     frozenset({CHILDREN_COWORKER, CHILDREN_ORGANIZER, PARTICIPANT})),
    ("datagrid_assembly_all_attendances",
     f"/occasions/{DIVISION_SLUGS[3]}/{AssemblySlugs.JUNIOR_REGULAR}"
     "/datagrid_assembly_all_attendances/",
     frozenset({CHILDREN_COWORKER, CHILDREN_ORGANIZER, DATA_ORGANIZER})),
)

#: Pages behind ``RouteAndSpyGuard``: refusal is Django's 403 page, not the
#: explanatory 200 body that ``RouteGuard`` alone produces.
SPY_GUARDED = frozenset(
    {"attendee_update_self", "attendee_create_view", "attendee_update_view"}
)

#: Logins the spy half lets through even though their auth group does not:
#: Grace opening her own record, and her father, who is her scheduler.
EXTRA_ALLOWED = {
    "attendee_update_view": frozenset({"golden_youth", "golden_member"}),
}

#: The outsider has no organization at all, so pages that read
#: ``request.user.organization.infos`` cannot serve them; they are covered by
#: the API tests instead, where organization scoping is the thing under test.
MATRIX_PERSONAS = tuple(
    persona for persona in PERSONAS if persona.username != "golden_outsider"
)


def _resolve(path, golden):
    return path(golden) if callable(path) else path


@pytest.mark.parametrize(
    "page", PAGES, ids=[page[0] for page in PAGES]
)
@pytest.mark.parametrize(
    "persona", MATRIX_PERSONAS, ids=[persona.username for persona in MATRIX_PERSONAS]
)
def test_route_guard_matrix(golden, login, page, persona):
    """Only the auth groups the seed grants may open each page."""
    name, path, allowed_groups = page
    should_be_allowed = bool(set(persona.groups) & allowed_groups) or (
        persona.username in EXTRA_ALLOWED.get(name, ())
    )

    client = login(persona.username)
    response = client.get(_resolve(path, golden))
    body = response.content.decode()
    refused = (
        response.status_code == 403 if name in SPY_GUARDED else ROUTE_REFUSED in body
    )

    if should_be_allowed:
        assert not refused, f"{persona.username} was refused {name}"
    else:
        assert refused, f"{persona.username} got into {name}"


def test_anonymous_users_are_sent_to_the_login_page(client, golden):
    for _name, path, _groups in PAGES:
        response = client.get(_resolve(path, golden))
        assert response.status_code == 302, path
        assert "/accounts/login/" in response["Location"], path


def test_a_superuser_without_groups_is_still_refused_by_the_route_guard(golden, login):
    """RouteGuard reads auth groups, not ``is_superuser`` — worth pinning."""
    client = login("golden_superuser")
    response = client.get("/persons/attendees/")
    assert ROUTE_REFUSED in response.content.decode()
