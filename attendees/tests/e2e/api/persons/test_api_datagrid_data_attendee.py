"""``/persons/api/datagrid_data_attendee/`` against the golden congregation."""

import pytest

from attendees.persons.models import Attendee
from attendees.tests.golden.constants import Relations
from attendees.tests.e2e.helpers import target

pytestmark = pytest.mark.django_db


class TestDatagridDataAttendee:
    def test_a_bare_list_is_the_whole_organization_paginated(self, golden, api_login):
        """It used to raise UnboundLocalError."""
        client = api_login("golden_data_organizer")
        response = client.get("/persons/api/datagrid_data_attendee/")
        assert response.status_code == 200
        payload = response.json()
        assert payload["totalCount"] == 350
        assert len(payload["data"]) == 20  # CustomStorePagination, PAGE_SIZE 20

    def test_the_list_is_ordered_so_paging_is_stable(self, golden, api_login):
        client = api_login("golden_data_organizer")
        first = client.get("/persons/api/datagrid_data_attendee/?take=25").json()
        again = client.get("/persons/api/datagrid_data_attendee/?take=25").json()
        assert [row["id"] for row in first["data"]] == [
            row["id"] for row in again["data"]
        ]

    def test_a_single_attendee_comes_back_with_their_participations(
        self, golden, api_login
    ):
        grace = golden.attendee("chen_grace")
        client = api_login("golden_data_organizer")
        response = client.get(f"/persons/api/datagrid_data_attendee/{grace.id}/")
        assert response.status_code == 200
        row = response.json()
        assert row["first_name"] == "Grace"
        assert row["last_name2"] == "陳"
        assert row["organization_slug"].endswith("cfcc_hayward")
        assert row["attendingmeets"]

    def test_searching_matches_the_han_name(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/persons/api/datagrid_data_attendee/?searchValue=陳明恩")
        assert response.status_code == 200
        names = [row["first_name"] for row in response.json()["data"]]
        assert "Grace" in names

    def test_searching_matches_the_simplified_form_too(self, golden, api_login):
        """opencc_convert writes both scripts, so either spelling finds the same people."""
        client = api_login("golden_data_organizer")
        traditional = client.get("/persons/api/datagrid_data_attendee/?searchValue=陳明恩")
        simplified = client.get("/persons/api/datagrid_data_attendee/?searchValue=陈明恩")
        assert simplified.json()["totalCount"] == traditional.json()["totalCount"]
        assert {row["id"] for row in simplified.json()["data"]} == {
            row["id"] for row in traditional.json()["data"]
        }
        # 明恩 is a common given name: Grace is one of several people it finds.
        assert str(golden.attendee("chen_grace").id) in {
            row["id"] for row in simplified.json()["data"]
        }

    def test_the_soft_deleted_household_never_appears(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/datagrid_data_attendee/?searchValue=peng_jinlong@example.org"
        )
        assert response.json()["totalCount"] == 0

    def test_an_outsider_sees_nothing(self, golden, api_login):
        client = api_login("golden_outsider")
        response = client.get("/persons/api/datagrid_data_attendee/")
        assert response.status_code == 200
        assert response.json()["totalCount"] == 0

    def test_a_data_admin_can_create_an_attendee_with_a_new_family(
        self, golden, api_login
    ):
        client = api_login("golden_data_organizer")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID="new",
            HTTP_X_ADD_FOLK="new",
            HTTP_X_FOLK_ROLE=str(Relations.FATHER),
        )
        response = client.post(
            "/persons/api/datagrid_data_attendee/",
            {
                "first_name": "Newcomer",
                "last_name": "Yeh",
                "last_name2": "葉",
                "first_name2": "新來",
                "gender": "MALE",
                "division": 1,
                "infos": {"names": {}, "fixed": {}, "contacts": {}},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        created = Attendee.objects.get(pk=response.json()["id"])
        assert created.infos["names"]["original"] == "Newcomer Yeh 葉新來"
        assert created.families.count() == 1

    def test_an_api_client_may_send_only_the_infos_it_knows(self, golden, api_login):
        """A server-to-server client (Tally) sends fixed and contacts and nothing
        else; the server completes the sections it derives or indexes itself."""
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID="new")
        response = client.post(
            "/persons/api/datagrid_data_attendee/",
            {
                "first_name": "Visitor",
                "last_name": "Lam",
                "gender": "UNSPECIFIED",
                "division": 1,
                "infos": {"fixed": {"grade": 15}, "contacts": {}},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        created = Attendee.objects.get(pk=response.json()["id"])
        assert created.infos["names"]["original"] == "Visitor Lam"
        assert created.infos["fixed"] == {"grade": 15}
        assert set(created.infos) >= {"names", "fixed", "contacts", "emergency_contacts", "progressions", "schedulers", "updating_attendees"}

    def test_updating_an_attendee_rewrites_the_derived_names(self, golden, api_login):
        """A partial edit must still refresh the searchable name.

        The datagrid serializer saves through ``update_or_create``, which since
        Django 4.2 passes ``update_fields=set(defaults)``.  ``Attendee.save``
        derives ``infos["names"]`` on every save, so unless it adds ``infos``
        back to ``update_fields`` the derived names are computed and thrown
        away — and search keeps finding the old spelling.
        """
        chloe = golden.attendee("wong_chloe")
        client = target(api_login("golden_data_organizer"), chloe)
        response = client.patch(
            f"/persons/api/datagrid_data_attendee/{chloe.id}/",
            {"first_name2": "佳恩", "last_name2": "黃"},
            format="json",
        )
        assert response.status_code == 200, response.content
        chloe.refresh_from_db()
        assert chloe.infos["names"]["original"].endswith("黃佳恩")
        assert chloe.infos["names"]["simplified"].endswith("黄佳恩")

    def test_a_member_cannot_edit_a_stranger(self, golden, api_login):
        stranger = golden.attendee("guo_vivian")
        client = target(api_login("golden_member"), stranger)
        response = client.patch(
            f"/persons/api/datagrid_data_attendee/{stranger.id}/",
            {"first_name": "Hacked"},
            format="json",
        )
        assert response.status_code in (403, 404)
        stranger.refresh_from_db()
        assert stranger.first_name == "Vivian"

    def test_a_login_without_an_organization_reaches_no_data(self, golden, api_login):
        client = api_login("golden_outsider")
        response = client.get("/persons/api/datagrid_data_attendee/")
        assert response.json()["totalCount"] == 0

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

    def test_a_token_authenticated_client_is_served(self, golden, token_client):
        client = token_client("golden_data_organizer")
        response = client.get("/persons/api/datagrid_data_attendee/")
        assert response.status_code == 200, response.content

    def test_an_anonymous_call_is_refused_rather_than_redirected(self, golden, client):
        response = client.get("/persons/api/datagrid_data_attendee/")
        assert response.status_code == 403
