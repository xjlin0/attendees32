"""
The Tally server-to-server integration surface.

Three claims, each of which used to be false:

1. `setup_tally_integration` provisions everything Tally needs, idempotently.
2. A DRF token reaches every endpoint Tally calls — the Django-level login
   guards used to run before DRF authentication and 302-redirect token-only
   requests to the login page.
3. A bare list of `datagrid_data_attendee` is the caller's organization,
   paginated — it used to raise UnboundLocalError (HTTP 500), and it is how
   Tally sweeps the roster.

Session users keep working throughout: SessionAuthentication still runs first,
and the object-level privilege checks are byte-for-byte the same rules.
"""
import pytest
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connection
from rest_framework.test import APIClient

from attendees.occasions.models import Assembly, Character, Meet
from attendees.persons.models import Attendee, Category, Relation, Utility
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization():
    return Organization.objects.create(
        slug="testorg",
        display_name="Test Organization",
        infos={
            "acronym": "test",
            "contacts": {},
            "settings": {"attendee_to_attending": True},
            "counselor": [],
            "data_admins": [],
            "groups_see_all_meets_attendees": [],
            "default_time_zone": "America/Los_Angeles",
        },
    )


@pytest.fixture
def vocabulary():
    """The slice of fixtures/db_seed.json the integration stands on."""
    Category.objects.get_or_create(
        pk=Attendee.FAMILY_CATEGORY, defaults={"type": "folk", "display_name": "family", "infos": {}}
    )
    Category.objects.get_or_create(
        pk=Attendee.NON_FAMILY_CATEGORY, defaults={"type": "folk", "display_name": "other", "infos": {}}
    )
    Category.objects.get_or_create(pk=1, defaults={"type": "attendance", "display_name": "scheduled", "infos": {}})
    # Creating any attendee fires the post-save signal, which files them into
    # a hidden non-family folk with Relation pk 0.
    Relation.objects.get_or_create(
        pk=Attendee.HIDDEN_ROLE,
        defaults={"title": "hidden", "gender": "UNSPECIFIED", "reciprocal_ids": []},
    )
    Relation.objects.get_or_create(
        title="child", defaults={"gender": "UNSPECIFIED", "emergency_contact": True, "reciprocal_ids": []}
    )
    Relation.objects.get_or_create(
        title="parent", defaults={"gender": "UNSPECIFIED", "emergency_contact": True, "reciprocal_ids": []}
    )
    # Rows made with an explicit pk leave the id sequence behind them, and the
    # command's own creates would then collide. loaddata resets sequences the
    # same way after a fixture.
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), [Category, Relation]):
            cursor.execute(sql)


@pytest.fixture
def provisioned(organization, vocabulary):
    call_command("setup_tally_integration", "--organization-slug", "testorg")
    user = User.objects.get(username="tally-integration")
    return {
        "organization": organization,
        "user": user,
        "token": user.auth_token.key,
        "division": Division.objects.get(slug="testorg_tally_youth"),
        "assembly": Assembly.objects.get(slug="testorg_tally_youth_ministry"),
        "meet": Meet.objects.get(slug="testorg_tally_gathering"),
        "character": Character.objects.get(slug="testorg_tally_student"),
    }


def token_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


class TestSetupCommand:
    def test_provisions_everything(self, provisioned):
        user = provisioned["user"]
        assert user.groups.filter(name="tally_integration").exists()
        assert Attendee.objects.filter(user=user).exists()
        org = Organization.objects.get(slug="testorg")
        assert "tally_integration" in org.infos["groups_see_all_meets_attendees"]
        assert "tally_integration" in org.infos["counselor"]

    def test_is_idempotent(self, provisioned):
        counts = (
            Division.objects.count(),
            Assembly.objects.count(),
            Meet.objects.count(),
            Character.objects.count(),
            User.objects.count(),
            Attendee.objects.count(),
        )
        call_command("setup_tally_integration", "--organization-slug", "testorg")
        assert counts == (
            Division.objects.count(),
            Assembly.objects.count(),
            Meet.objects.count(),
            Character.objects.count(),
            User.objects.count(),
            Attendee.objects.count(),
        )


class TestTokenAuthentication:
    def test_bare_attendee_list_is_the_paginated_org(self, provisioned):
        response = token_client(provisioned["token"]).get(
            "/persons/api/datagrid_data_attendee/", {"take": 5, "skip": 0}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["totalCount"] >= 1  # at least the integration attendee
        assert isinstance(body["data"], list)

    def test_search_reaches_the_org(self, provisioned):
        response = token_client(provisioned["token"]).get(
            "/persons/api/datagrid_data_attendee/", {"searchValue": "Tally", "take": 5}
        )
        assert response.status_code == 200

    def test_every_read_endpoint_answers_json_not_a_redirect(self, provisioned):
        meet = provisioned["meet"]
        assembly = provisioned["assembly"]
        attendee = Attendee.objects.get(user=provisioned["user"])
        client = token_client(provisioned["token"])

        reads = [
            ("/persons/api/all_relations/", {}, {}),
            ("/occasions/api/organization_meets/", {"assemblies[]": assembly.id}, {}),
            ("/occasions/api/organization_team_gatherings/", {"meets[]": meet.slug}, {}),
            (
                "/occasions/api/organization_meet_character_attendances/",
                {"meets[]": meet.slug},
                {},
            ),
            (
                "/persons/api/attendee_attendings/",
                {},
                {"HTTP_X_TARGET_ATTENDEE_ID": str(attendee.id)},
            ),
            (
                "/persons/api/attendee_families/",
                {},
                {"HTTP_X_TARGET_ATTENDEE_ID": str(attendee.id)},
            ),
        ]
        for path, params, headers in reads:
            response = client.get(path, params, **headers)
            assert response.status_code == 200, f"{path} -> {response.status_code}"

    def test_anonymous_gets_a_401_not_a_login_redirect(self, provisioned):
        response = APIClient().get("/persons/api/datagrid_data_attendee/", {"take": 5})
        assert response.status_code in (401, 403)

    def test_a_session_user_still_gets_in(self, provisioned):
        client = APIClient()
        client.force_login(provisioned["user"])
        response = client.get("/persons/api/datagrid_data_attendee/", {"take": 5})
        assert response.status_code == 200

    def test_spyguard_still_blocks_an_out_of_reach_attendee(self, provisioned, vocabulary):
        other_org = Organization.objects.create(
            slug="otherorg", display_name="Other", infos={"groups_see_all_meets_attendees": []}
        )
        other_division = Division.objects.create(
            organization=other_org,
            slug="otherorg_division",
            display_name="Other",
            audience_auth_group=provisioned["user"].groups.first(),
            infos={},
        )
        stranger = Attendee.objects.create(
            division=other_division,
            first_name="Not",
            last_name="Yours",
            gender="UNSPECIFIED",
            infos=Utility.attendee_infos(),
        )

        response = token_client(provisioned["token"]).get(
            "/persons/api/attendee_families/",
            {},
            HTTP_X_TARGET_ATTENDEE_ID=str(stranger.id),
        )
        assert response.status_code == 403


class TestMergedAttendees:
    """What an id that was merged away answers.

    A merged-away attendee answers `410 Gone` with the primary's id, and an
    integration that holds the old id follows it. Before the merge existed, a
    merged attendee here was a soft-delete: the id 404ed, indistinguishable
    from a typo, and silent about the fact that the person still exists under
    a different id.
    """

    def _attendee(self, provisioned, first_name):
        return Attendee.objects.create(
            first_name=first_name,
            last_name="Chen",
            division=provisioned["division"],
            gender="unspecified",
            infos=Utility.attendee_infos(),
        )

    def test_a_merged_id_answers_410_with_the_primary(self, provisioned):
        primary = self._attendee(provisioned, "Ava")
        duplicate = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])

        merged = client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(primary.id)},
            format="json",
        )
        assert merged.status_code == 200
        assert merged.json()["merged_into"] == str(primary.id)

        response = client.get(f"/persons/api/datagrid_data_attendee/{duplicate.id}/")
        assert response.status_code == 410
        assert response.json()["merged_into"] == str(primary.id)

    def test_the_primary_is_still_readable(self, provisioned):
        primary = self._attendee(provisioned, "Ava")
        duplicate = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])
        client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(primary.id)},
            format="json",
        )

        response = client.get(f"/persons/api/datagrid_data_attendee/{primary.id}/")
        assert response.status_code == 200

    def test_a_chain_reports_its_end(self, provisioned):
        """A into B on Sunday, B into C on Wednesday: A must answer C.

        Reporting B would send a caller to another tombstone and cost them a
        second round trip to find that out — and a caller that does not follow
        chains would record a dead id as live.
        """
        first = self._attendee(provisioned, "Ava")
        second = self._attendee(provisioned, "Ava")
        third = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])

        client.post(
            f"/persons/api/datagrid_data_attendee/{first.id}/merge/",
            {"primary": str(second.id)},
            format="json",
        )
        client.post(
            f"/persons/api/datagrid_data_attendee/{second.id}/merge/",
            {"primary": str(third.id)},
            format="json",
        )

        response = client.get(f"/persons/api/datagrid_data_attendee/{first.id}/")
        assert response.status_code == 410
        assert response.json()["merged_into"] == str(third.id)

    def test_a_trail_that_ends_nowhere_is_gone_without_a_forwarding_address(
        self, provisioned
    ):
        primary = self._attendee(provisioned, "Ava")
        duplicate = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])
        client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(primary.id)},
            format="json",
        )
        primary.is_removed = True
        primary.save(update_fields=["is_removed"])

        response = client.get(f"/persons/api/datagrid_data_attendee/{duplicate.id}/")
        assert response.status_code == 410
        # "Gone, and nobody holds them now" is a different answer from "gone,
        # ask over there", and a caller that cannot tell them apart keeps
        # chasing.
        assert "merged_into" not in response.json()

    def test_a_deleted_but_never_merged_attendee_is_still_served(self, provisioned):
        """Only a merge forwards. The attendee page shows a plain deletion as
        "Deleted record of …", so its id keeps answering with the record."""
        deleted = self._attendee(provisioned, "Ava")
        deleted.is_removed = True
        deleted.save(update_fields=["is_removed"])

        response = token_client(provisioned["token"]).get(
            f"/persons/api/datagrid_data_attendee/{deleted.id}/"
        )
        assert response.status_code == 200
        assert response.json()["is_removed"] is True

    def test_an_id_nobody_ever_held_is_still_a_404(self, provisioned):
        response = token_client(provisioned["token"]).get(
            "/persons/api/datagrid_data_attendee/8ec6a0f6-0000-4000-8000-000000000000/"
        )
        assert response.status_code == 404

    def test_a_merged_attendee_leaves_the_roster_sweep(self, provisioned):
        primary = self._attendee(provisioned, "Ava")
        duplicate = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])
        client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(primary.id)},
            format="json",
        )

        listed = client.get(
            "/persons/api/datagrid_data_attendee/", {"take": 100, "skip": 0}
        ).json()["data"]
        ids = {row["id"] for row in listed}
        assert str(primary.id) in ids
        assert str(duplicate.id) not in ids

    def test_refuses_a_merge_it_cannot_make_sense_of(self, provisioned):
        duplicate = self._attendee(provisioned, "Ava")
        client = token_client(provisioned["token"])

        response = client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(duplicate.id)},
            format="json",
        )
        assert response.status_code == 400
