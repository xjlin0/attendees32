"""``/persons/api/categorized_pasts/`` against the golden congregation."""

import pytest

from attendees.persons.models import Attendee
from attendees.persons.models import AttendingMeet
from attendees.persons.models import Past
from attendees.tests.golden.constants import MeetSlugs
from attendees.tests.golden.constants import NoteCategory
from attendees.tests.golden.constants import StatusCategory
from attendees.tests.e2e.helpers import attendee_content_type_id, notes_for, target

pytestmark = pytest.mark.django_db


class TestCategorizedPasts:
    def test_statuses_are_listed_for_a_privileged_user(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.get(
            "/persons/api/categorized_pasts/", {"category__type": "status"}
        )
        assert response.status_code == 200
        categories = {row["category"] for row in response.json()["data"]}
        assert StatusCategory.BAPTIZED in categories
        assert StatusCategory.MEMBER in categories

    def test_education_history_is_listed(self, golden, api_login):
        pastor = golden.attendee("zhang_zhongxin")
        client = target(api_login("golden_data_organizer"), pastor)
        response = client.get(
            "/persons/api/categorized_pasts/", {"category__type": "education"}
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_a_data_admin_can_add_a_baptism(self, golden, api_login):
        feng = golden.attendee("feng_ruian")
        assert not Past.objects.filter(
            object_id=str(feng.id), category_id=StatusCategory.BAPTIZED
        ).exists()
        client = target(api_login("golden_data_organizer"), feng)
        response = client.post(
            "/persons/api/categorized_pasts/",
            {
                "category": StatusCategory.BAPTIZED,
                "content_type": attendee_content_type_id(),
                "object_id": str(feng.id),
                "display_name": "受洗 baptised at CFCCH",
                "when": "2026-04-05",
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        assert Past.objects.filter(
            object_id=str(feng.id), category_id=StatusCategory.BAPTIZED
        ).exists()

    def test_adding_a_baptism_opens_the_baptised_participation(self, golden, api_login):
        """The Past post-save signal, over HTTP."""
        feng = golden.attendee("feng_xinyi")
        client = target(api_login("golden_data_organizer"), feng)
        client.post(
            "/persons/api/categorized_pasts/",
            {
                "category": StatusCategory.BAPTIZED,
                "content_type": attendee_content_type_id(),
                "object_id": str(feng.id),
                "display_name": "受洗",
                "when": "2026-04-05",
            },
            format="json",
        )
        assert AttendingMeet.objects.filter(
            meet__slug=MeetSlugs.BAPTIZED, attending__attendee=feng
        ).exists()

    def test_an_ordinary_member_cannot_write_someone_elses_past(self, golden, api_login):
        stranger = golden.attendee("wong_wilson")
        client = target(api_login("golden_member"), stranger)
        response = client.post(
            "/persons/api/categorized_pasts/",
            {
                "category": StatusCategory.MEMBER,
                "content_type": attendee_content_type_id(),
                "object_id": str(stranger.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_a_counseling_note_reaches_only_the_counselor(self, golden, api_login):
        meiling = golden.attendee("liu_meiling")

        counselor = notes_for(api_login("golden_counselor"), meiling)
        assert counselor.status_code == 200
        assert any(
            row["category"] == NoteCategory.COUNSELING
            for row in counselor.json()["data"]
        )

        # A data admin is privileged, but the note is not addressed to them.
        admin = notes_for(api_login("golden_data_organizer"), meiling)
        assert admin.status_code == 200
        assert not any(
            row["category"] == NoteCategory.COUNSELING for row in admin.json()["data"]
        )

    def test_a_coworker_note_reaches_only_the_named_coworker(self, golden, api_login):
        kevin = golden.attendee("xu_kevin")
        organizer = notes_for(api_login("golden_children_organizer"), kevin)
        assert any(
            row["category"] == NoteCategory.COWORKER
            for row in organizer.json()["data"]
        ), "the note names the children's organizer"

        other = notes_for(api_login("golden_conference_organizer"), kevin)
        assert not any(
            row["category"] == NoteCategory.COWORKER for row in other.json()["data"]
        )

    def test_public_notes_are_visible_to_an_ordinary_reader(self, golden, api_login):
        public = Past.objects.filter(category_id=NoteCategory.PUBLIC).first()
        assert public is not None
        attendee = Attendee.objects.get(pk=public.object_id)
        response = notes_for(api_login("golden_children_organizer"), attendee)
        assert response.status_code == 200
        assert any(
            row["category"] == NoteCategory.PUBLIC for row in response.json()["data"]
        )

    def test_a_youth_cannot_grant_themselves_membership(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = api_login("golden_youth")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(grace.id))
        before = Past.objects.filter(
            object_id=str(grace.id), category_id=StatusCategory.MEMBER
        ).count()
        response = client.post(
            "/persons/api/categorized_pasts/",
            {"category": StatusCategory.MEMBER, "object_id": str(grace.id)},
            format="json",
        )
        assert response.status_code in (400, 403)
        assert (
            Past.objects.filter(
                object_id=str(grace.id), category_id=StatusCategory.MEMBER
            ).count()
            == before
        )
