"""The server-to-server surface, against the whole golden congregation.

``attendees/persons/tests/test_tally_integration.py`` proves the contract on a
minimal fixture.  This module proves it at the size Tally actually meets: a
350-person roster it has to page through, families it has to file quick-added
visitors into, and a check-in history it has to write back.
"""

import pytest
from django.core.management import call_command
from rest_framework.authtoken.models import Token

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, AttendingMeet, Folk, Relation
from attendees.tests.golden.constants import ORGANIZATION_SLUG
from attendees.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def tally(golden):
    """Provision the integration and hand back an authenticated client."""
    from rest_framework.test import APIClient

    call_command(
        "setup_tally_integration", organization_slug=ORGANIZATION_SLUG, verbosity=0
    )
    user = User.objects.get(username="tally-integration")
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


class TestProvisioning:
    def test_the_command_is_idempotent(self, golden):
        call_command(
            "setup_tally_integration", organization_slug=ORGANIZATION_SLUG, verbosity=0
        )
        before = (
            Meet.objects.count(),
            Attendee.all_objects.count(),
            User.objects.count(),
        )
        call_command(
            "setup_tally_integration", organization_slug=ORGANIZATION_SLUG, verbosity=0
        )
        after = (
            Meet.objects.count(),
            Attendee.all_objects.count(),
            User.objects.count(),
        )
        assert before == after

    def test_it_refuses_an_unknown_organization(self, golden):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command(
                "setup_tally_integration", organization_slug="no-such-church",
                verbosity=0,
            )


class TestTokenAuthentication:
    def test_a_token_reaches_the_roster(self, tally):
        response = tally.get("/persons/api/datagrid_data_attendee/")
        assert response.status_code == 200
        assert response.json()["totalCount"] == 351  # 350 people + the integration

    def test_no_token_is_refused_rather_than_redirected(self, golden):
        from rest_framework.test import APIClient

        response = APIClient().get("/persons/api/datagrid_data_attendee/")
        assert response.status_code in (401, 403)

    def test_a_bad_token_is_refused(self, golden):
        from rest_framework.test import APIClient

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
        assert client.get("/persons/api/datagrid_data_attendee/").status_code in (
            401, 403
        )


class TestRosterSweep:
    def test_paging_covers_every_person_exactly_once(self, tally):
        seen = []
        skip, take = 0, 100
        while True:
            page = tally.get(
                "/persons/api/datagrid_data_attendee/",
                {"skip": skip, "take": take},
            ).json()
            seen.extend(row["id"] for row in page["data"])
            skip += take
            if skip >= page["totalCount"]:
                break
        assert len(seen) == len(set(seen)) == 351

    def test_a_swept_row_carries_what_a_check_in_app_needs(self, tally, golden):
        grace = golden.attendee("chen_grace")
        row = tally.get(f"/persons/api/datagrid_data_attendee/{grace.id}/").json()
        assert row["first_name"] == "Grace"
        assert row["infos"]["names"]["original"]
        assert row["infos"]["fixed"]["grade"] == 15
        assert row["actual_birthday"]
        assert row["places"] == [] or isinstance(row["places"], list)
        assert row["folkattendee_set"]

    def test_the_sweep_never_returns_the_departed(self, tally, golden):
        page = tally.get(
            "/persons/api/datagrid_data_attendee/", {"take": 500}
        ).json()
        ids = {row["id"] for row in page["data"]}
        assert str(golden.attendee("peng_jinlong").id) not in ids


class TestQuickAdd:
    def test_a_visitor_can_be_created_with_a_new_family(self, tally, golden):
        division = Attendee.objects.get(
            pk=golden.attendee("chen_grace").id
        ).division_id
        tally.credentials(
            HTTP_AUTHORIZATION=tally._credentials["HTTP_AUTHORIZATION"],
            HTTP_X_TARGET_ATTENDEE_ID="new",
            HTTP_X_ADD_FOLK="new",
            HTTP_X_FOLK_ROLE=str(Relation.objects.get(title="child").pk),
        )
        response = tally.post(
            "/persons/api/datagrid_data_attendee/",
            {
                "first_name": "Walkin",
                "last_name": "Visitor",
                "gender": "UNSPECIFIED",
                "division": division,
                "infos": {"names": {}, "fixed": {}, "contacts": {}},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        created = Attendee.objects.get(pk=response.json()["id"])
        assert created.families.count() == 1
        assert Folk.objects.filter(
            pk=created.families.first().pk, category_id=0
        ).exists()

    def test_a_quick_added_person_can_join_a_meet(self, tally, golden):
        meet = Meet.objects.get(slug=f"{ORGANIZATION_SLUG}_tally_gathering")
        newcomer = golden.attendee("feng_ruian")
        tally.credentials(
            HTTP_AUTHORIZATION=tally._credentials["HTTP_AUTHORIZATION"],
            HTTP_X_TARGET_ATTENDEE_ID=str(newcomer.id),
        )
        response = tally.put(
            "/persons/api/default_attendingmeets/",
            {"action": "join", "meet": meet.slug},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert AttendingMeet.objects.filter(
            meet=meet, attending__attendee=newcomer
        ).exists()
