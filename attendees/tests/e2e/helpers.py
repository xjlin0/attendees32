"""Constants and small helpers shared by the golden end-to-end tests."""

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType

from attendees.occasions.models import Assembly
from attendees.persons.models import Attendee
from attendees.persons.models import Utility
from attendees.tests.golden.constants import DIVISION_SLUGS

DIVISION_JUNIOR = DIVISION_SLUGS[3]
DIVISION_DATA = DIVISION_SLUGS[5]
JUNIOR_STUDENT_SLUG = "d7c8Fd_cfcch_kid_student"
CONGREGATION_SLUG = "d7c8Fd_cfcch_congregation_data_roster"
REFUSED = "you do not have permissions to visit this"
REGISTRATIONS = "/persons/api/all_registrations/"
ROUTE_REFUSED = "does not have permissions to visit such route"


def window():
    now = Utility.now_with_timezone()
    return {
        "start": (now - timedelta(weeks=12)).isoformat(),
        "finish": (now + timedelta(weeks=2)).isoformat(),
    }


def attendee_content_type_id():
    return ContentType.objects.get_for_model(Attendee).id


def target(api_client, attendee):
    """Point ``api_client`` at ``attendee`` via the X-Target-Attendee-Id header.

    ``APIClient.credentials()`` replaces every header it holds, so the ones
    already set (a token client's Authorization) are carried over.
    """
    api_client.credentials(
        **{**api_client._credentials, "HTTP_X_TARGET_ATTENDEE_ID": str(attendee.id)}
    )
    return api_client


def retreat_assembly() -> Assembly:
    return Assembly.objects.get(slug="cfcch_summer_retreat_2025")


def notes_for(client, attendee):
    client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(attendee.id))
    return client.get("/persons/api/categorized_pasts/", {"category__type": "note"})
