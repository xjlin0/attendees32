"""``/occasions/api/organization_meet_character_attendances/`` against the golden congregation."""

import pytest

from attendees.occasions.models import Attendance
from attendees.occasions.models import Gathering
from attendees.persons.models import Attending
from attendees.tests.golden.constants import AttendanceCategory
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.e2e.helpers import CONGREGATION_SLUG, window

pytestmark = pytest.mark.django_db


class TestOrganizationMeetCharacterAttendances:
    def test_attendances_are_listed_for_a_meet_and_character(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_character_attendances/",
            {
                "meets[]": MeetSlugs.CHINESE_SERVICE,
                "characters[]": CONGREGATION_SLUG,
                **window(),
                "take": 10,
            },
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 100

    def test_an_attendance_can_be_recorded_and_removed(self, golden, api_login):
        gathering = Gathering.objects.filter(
            meet__slug=MeetSlugs.CHINESE_SERVICE
        ).order_by("-start").first()
        # Somebody on the roster who was not marked at that gathering — the
        # dataset deliberately leaves gaps, nobody attends every single week.
        attending = (
            Attending.objects.filter(
                attendingmeet__meet=gathering.meet,
            )
            .exclude(attendance__gathering=gathering)
            .distinct()
            .first()
        )
        assert attending is not None

        client = api_login("golden_data_organizer")
        response = client.post(
            "/occasions/api/organization_meet_character_attendances/",
            {
                "gathering": gathering.pk,
                "attending": attending.pk,
                "character": 15,
                "category": AttendanceCategory.ATTENDED,
                "start": gathering.start.isoformat(),
                "finish": gathering.finish.isoformat(),
                "infos": {},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        created = Attendance.objects.get(gathering=gathering, attending=attending)

        deleted = client.delete(
            f"/occasions/api/organization_meet_character_attendances/{created.pk}/"
        )
        assert deleted.status_code in (200, 204), deleted.content
