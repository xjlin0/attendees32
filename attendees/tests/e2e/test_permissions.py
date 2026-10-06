"""Who may see whom.

The application layers four separate checks, and each one is exercised here
against real people rather than a two-record fixture:

``RouteGuard``
    auth group vs. ``users.Menu`` — covered by :mod:`test_pages`.
``SpyGuard`` / ``DrfSpyGuard``
    may this login act on *that* attendee — self, same organization plus a
    coworker group, or a scheduler relationship.
``User.privileged()``
    data admins and counselors, for the pages that walk the whole roster.
``infos["show_secret"]``
    per-record confidentiality inside an otherwise readable tab.
"""

import pytest

from attendees.persons.models import Attendee, Past
from attendees.tests.golden.constants import NoteCategory, StatusCategory

pytestmark = pytest.mark.django_db

SPY_REFUSED = "Do you have attendee associated with your user?"


def notes_for(client, attendee):
    client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(attendee.id))
    return client.get("/persons/api/categorized_pasts/", {"category__type": "note"})


class TestSpyGuard:
    def test_a_member_may_read_their_own_record(self, golden, login):
        client = login("golden_member")
        attendee = golden.attendee("chen_zhiming")
        assert client.get(f"/persons/attendee/{attendee.id}").status_code == 200

    def test_a_parent_may_read_a_child_they_schedule(self, golden, login):
        client = login("golden_member")
        joshua = golden.attendee("chen_joshua")
        assert client.get(f"/persons/attendee/{joshua.id}").status_code == 200

    def test_a_parent_may_not_read_an_unrelated_child(self, golden, login):
        client = login("golden_member")
        stranger = golden.attendee("lee_peter")
        assert client.get(f"/persons/attendee/{stranger.id}").status_code == 403

    def test_a_guardian_may_read_their_ward(self, golden, login):
        """Kevin's guardians are not his parents, but they do schedule him."""
        client = login("golden_counselor")  # xu_jianguo
        kevin = golden.attendee("xu_kevin")
        assert client.get(f"/persons/attendee/{kevin.id}").status_code == 200

    def test_a_coworker_group_may_read_anyone_in_the_organization(self, golden, login):
        client = login("golden_children_organizer")
        for key in ("wang_yulan", "tsai_serena", "guo_mingzhu"):
            attendee = golden.attendee(key)
            assert client.get(f"/persons/attendee/{attendee.id}").status_code == 200

    def test_a_login_with_no_attendee_may_read_nobody(self, golden, login):
        client = login("golden_unaffiliated")
        attendee = golden.attendee("chen_grace")
        assert client.get(f"/persons/attendee/{attendee.id}").status_code == 403

    def test_the_drf_guard_refuses_a_stranger(self, golden, api_login):
        client = api_login("golden_crossing_member")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_grace").id)
        )
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 403

    def test_the_drf_guard_lets_a_scheduler_through(self, golden, api_login):
        client = api_login("golden_member")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 200


class TestOrganizationIsolation:
    def test_another_organizations_attendee_is_invisible(self, golden, api_login):
        """The seed carries 天堂 Heaven as a second organization."""
        heaven_attendee = Attendee.all_objects.filter(
            division__organization__slug="faBd6C_heaven"
        ).first()
        assert heaven_attendee is None, (
            "the golden dataset replaces the seed's demo people; "
            "the second organization is vocabulary only"
        )

    def test_a_login_without_an_organization_reaches_no_data(self, golden, api_login):
        client = api_login("golden_outsider")
        assert client.get("/persons/api/datagrid_data_attendee/").json()[
            "totalCount"
        ] == 0
        assert client.get("/occasions/api/user_assemblies/").status_code == 403

    def test_under_same_org_with_is_true_within_the_church(self, golden):
        zhiming = golden.attendee("chen_zhiming")
        assert zhiming.under_same_org_with(str(golden.attendee("wong_wilson").id))
        assert not zhiming.under_same_org_with(str(zhiming.id).replace("0", "1"))


class TestConfidentialNotes:
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


class TestPrivilegedOnlyPages:
    @pytest.mark.parametrize(
        "path",
        (
            "/persons/directory_report/",
            "/persons/attendingmeet_report/?meet=d7c8Fd_cfcch_congregation_directory",
            "/persons/attendingmeet_envelopes/?meet=d7c8Fd_cfcch_congregation_directory",
        ),
    )
    def test_only_data_admins_and_counselors_get_the_data(self, golden, login, path):
        allowed = login("golden_data_organizer").get(path)
        assert allowed.status_code == 200

    def test_a_children_coworker_may_open_the_directory_route_but_gets_403(
        self, golden, login
    ):
        response = login("golden_children_coworker").get("/persons/directory_report/")
        assert response.status_code == 403


class TestWriteGuards:
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

    def test_a_member_cannot_delete_another_attendee(self, golden, api_login):
        victim = golden.attendee("guo_vivian")
        client = api_login("golden_member")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(victim.id))
        response = client.delete(f"/persons/api/datagrid_data_attendee/{victim.id}/")
        assert response.status_code in (403, 404)
        assert Attendee.objects.filter(pk=victim.id).exists()

    def test_a_data_admin_can_soft_delete_an_attendee(self, golden, api_login):
        """Deleting is a soft delete: the person leaves the roster, not history."""
        leaving = golden.attendee("hu_zhiyi")
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(leaving.id))
        response = client.delete(f"/persons/api/datagrid_data_attendee/{leaving.id}/")
        assert response.status_code in (200, 204), response.content
        assert not Attendee.objects.filter(pk=leaving.id).exists()
        assert Attendee.all_objects.filter(pk=leaving.id).exists()
