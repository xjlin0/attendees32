"""``/persons/api/datagrid_data_attendee/`` against the golden congregation."""

import pytest

from attendees.persons.models import Attendee, Attending
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


class TestMergedAttendees:
    """A merged-away id answers 410 with the primary; a plain deletion still serves."""

    def _twins(self, golden):
        division = golden.attendee("chen_grace").division
        primary = Attendee.objects.create(first_name="Ava", last_name="Chen", division=division, gender="unspecified")
        duplicate = Attendee.objects.create(first_name="Ava", last_name="Chen", division=division, gender="unspecified")
        return primary, duplicate

    def _merge(self, client, duplicate, primary):
        return client.post(
            f"/persons/api/datagrid_data_attendee/{duplicate.id}/merge/",
            {"primary": str(primary.id)},
            format="json",
        )

    def test_a_merged_id_answers_410_with_the_primary(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        client = token_client("golden_data_organizer")
        merged = self._merge(client, duplicate, primary)
        assert merged.status_code == 200, merged.content
        assert merged.json()["merged_into"] == str(primary.id)

        response = client.get(f"/persons/api/datagrid_data_attendee/{duplicate.id}/")
        assert response.status_code == 410
        assert response.json()["merged_into"] == str(primary.id)
        assert client.get(f"/persons/api/datagrid_data_attendee/{primary.id}/").status_code == 200

    def test_a_chain_reports_its_end(self, golden, token_client):
        """A into B on Sunday, B into C on Wednesday: A must answer C, not B."""
        first, second = self._twins(golden)
        third = Attendee.objects.create(first_name="Ava", last_name="Chen", division=first.division, gender="unspecified")
        client = token_client("golden_data_organizer")
        self._merge(client, first, second)
        self._merge(client, second, third)

        response = client.get(f"/persons/api/datagrid_data_attendee/{first.id}/")
        assert response.status_code == 410
        assert response.json()["merged_into"] == str(third.id)
        # And not by walking: the second merge re-pointed the first tombstone.
        assert Attendee.all_objects.get(pk=first.pk).merged_into_id == third.id

    def test_a_trail_that_ends_nowhere_is_gone_without_a_forwarding_address(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        client = token_client("golden_data_organizer")
        self._merge(client, duplicate, primary)
        primary.is_removed = True
        primary.save(update_fields=["is_removed"])

        response = client.get(f"/persons/api/datagrid_data_attendee/{duplicate.id}/")
        assert response.status_code == 410
        assert "merged_into" not in response.json()

    def test_a_deleted_but_never_merged_attendee_is_still_served(self, golden, token_client):
        """Only a merge forwards; a plain deletion keeps answering with the record."""
        deleted = golden.attendee("peng_jinlong")
        assert deleted.is_removed
        response = token_client("golden_data_organizer").get(f"/persons/api/datagrid_data_attendee/{deleted.id}/")
        assert response.status_code == 200
        assert response.json()["is_removed"] is True

    def test_a_merged_attendee_leaves_the_list_and_its_attendance_moves(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        client = token_client("golden_data_organizer")
        self._merge(client, duplicate, primary)

        ids = {row["id"] for row in client.get("/persons/api/datagrid_data_attendee/", {"take": 400}).json()["data"]}
        assert str(primary.id) in ids
        assert str(duplicate.id) not in ids
        # The attending the create signal made folds into the primary's own.
        assert primary.attendings.filter(is_removed=False).count() == 1
        assert duplicate.attendings.filter(is_removed=False).count() == 0
        assert Attending.all_objects.filter(attendee=duplicate, is_removed=True).count() == 1

    def test_a_merge_is_refused_when_it_makes_no_sense(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        client = token_client("golden_data_organizer")
        assert self._merge(client, duplicate, duplicate).status_code == 400
        assert self._merge(client, duplicate, primary).status_code == 200
        # Into a record that was itself merged away.
        third = Attendee.objects.create(first_name="Ava", last_name="Chen", division=primary.division, gender="unspecified")
        assert self._merge(client, third, duplicate).status_code == 400

    def test_an_ordinary_member_cannot_merge(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        response = self._merge(token_client("golden_member"), duplicate, primary)
        assert response.status_code == 403
        assert Attendee.all_objects.get(pk=duplicate.pk).merged_into_id is None

    def _unmerge(self, client, duplicate):
        return client.post(f"/persons/api/datagrid_data_attendee/{duplicate.id}/unmerge/", format="json")

    def test_an_unmerge_puts_the_duplicate_back_once(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        client = token_client("golden_data_organizer")
        self._merge(client, duplicate, primary)

        response = self._unmerge(client, duplicate)
        assert response.status_code == 200, response.content
        assert response.json()["restored"] == str(duplicate.id)
        assert client.get(f"/persons/api/datagrid_data_attendee/{duplicate.id}/").status_code == 200
        assert duplicate.attendings.filter(is_removed=False).count() == 1
        assert primary.attendings.filter(is_removed=False).count() == 1
        # Once: the record is consumed.
        assert self._unmerge(client, duplicate).status_code == 400

    def test_an_ordinary_member_cannot_unmerge(self, golden, token_client):
        primary, duplicate = self._twins(golden)
        self._merge(token_client("golden_data_organizer"), duplicate, primary)
        assert self._unmerge(token_client("golden_member"), duplicate).status_code == 403
        assert Attendee.all_objects.get(pk=duplicate.pk).merged_into_id == primary.id
