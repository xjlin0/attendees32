"""Every ``/persons/api/…`` endpoint, read and write, against the golden church."""

import json

import pytest

from django.contrib.contenttypes.models import ContentType

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, AttendingMeet, Folk, Past
from attendees.tests.golden.constants import (
    AssemblySlugs,
    DIVISION_SLUGS,
    FolkCategory,
    MeetSlugs,
    Relations,
    StatusCategory,
)

pytestmark = pytest.mark.django_db

DIVISION_DATA = DIVISION_SLUGS[5]
DIVISION_JUNIOR = DIVISION_SLUGS[3]


def attendee_content_type_id():
    return ContentType.objects.get_for_model(Attendee).id


def target(api_client, attendee):
    api_client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(attendee.id))
    return api_client


# ------------------------------------------------------------------- rosters
class TestAttendeeRoster:
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

    def test_the_datagrid_roster_filters_by_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/datagrid_data_attendees/",
            {
                "filter": json.dumps(
                    ["attendings__meets__slug", "=", MeetSlugs.ENGLISH_SERVICE]
                )
            },
        )
        assert response.status_code == 200
        # 135 people are on the English service roster (100 adults, 25 youth and
        # the 10 bilingual attenders); the datagrid counts only participations
        # that have not finished, so the 15 inactive ones drop out.
        assert response.json()["totalCount"] == 120

    def test_the_datagrid_roster_accepts_a_devextreme_filter(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/datagrid_data_attendees/",
            {"filter": json.dumps(["last_name", "=", "Tsai"])},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 4

    def test_the_dead_are_excluded_unless_asked_for(self, golden, api_login):
        client = api_login("golden_data_organizer")
        without = client.get("/persons/api/datagrid_data_attendees/").json()["totalCount"]
        with_dead = client.get(
            "/persons/api/datagrid_data_attendees/?include_dead=true"
        ).json()["totalCount"]
        assert with_dead > without

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


# ------------------------------------------------------------------ families
class TestFamilyEndpoints:
    def test_an_attendees_families_are_listed(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.get("/persons/api/attendee_families/")
        assert response.status_code == 200
        assert any(
            row["display_name"].startswith("陳志明家")
            for row in response.json()["data"]
        )

    def test_family_membership_rows_carry_the_role(self, golden, api_login):
        grace = golden.attendee("chen_grace")
        client = target(api_login("golden_data_organizer"), grace)
        response = client.get(
            "/persons/api/datagrid_data_familyattendees/",
            {"categoryId": FolkCategory.FAMILY},
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert {row["attendee"] for row in rows} >= {
            str(golden.attendee("chen_zhiming").id),
            str(golden.attendee("chen_joshua").id),
        }
        assert {row["role"] for row in rows} >= {Relations.HUSBAND, Relations.SON}
        assert any(
            row["folk"]["display_name"].startswith("陳志明家") for row in rows
        )

    def test_other_relationships_come_from_the_same_endpoint(self, golden, api_login):
        kevin = golden.attendee("xu_kevin")
        client = target(api_login("golden_counselor"), kevin)
        response = client.get(
            "/persons/api/attendee_relationships/",
            {"categoryId": FolkCategory.OTHER},
        )
        assert response.status_code == 200
        roles = {row["role"] for row in response.json()["data"]}
        assert Relations.GUARDIAN in roles

    def test_related_attendees_are_reachable(self, golden, api_login):
        joshua = golden.attendee("chen_joshua")
        client = target(api_login("golden_member"), joshua)
        response = client.get("/persons/api/related_attendees/")
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_a_member_cannot_browse_a_stranger_relations(self, golden, api_login):
        stranger = golden.attendee("wong_wilson")
        client = target(api_login("golden_member"), stranger)
        response = client.get("/persons/api/related_attendees/")
        assert response.status_code == 403


# --------------------------------------------------------------------- pasts
class TestPastEndpoints:
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


# ------------------------------------------------------------- participations
class TestParticipationEndpoints:
    def test_an_attendees_participations_are_listed(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.get("/persons/api/datagrid_data_attendingmeet/")
        assert response.status_code == 200
        meet_ids = {row["meet"] for row in response.json()["data"]}
        assert Meet.objects.get(slug=MeetSlugs.CHINESE_SERVICE).id in meet_ids
        assert Meet.objects.get(slug=MeetSlugs.DIRECTORY).id in meet_ids

    def test_participations_can_be_queried_by_meet_and_character(
        self, golden, api_login
    ):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/organization_meet_character_attendingmeets/",
            {"meets[]": MeetSlugs.THE_ROCK, "characters[]": "d7c8Fd_cfcch_kid_student"},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 10

    def test_attendings_for_an_attendee_are_listed(self, golden, api_login):
        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.get("/persons/api/attendee_attendings/")
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_a_user_can_list_their_own_meets_attendings(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/user_meet_attendings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE},
        )
        assert response.status_code == 200

    def test_family_attendings_are_listed_for_a_parent(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/family_organization_attendings/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200

    def test_assembly_scoped_attendings_and_attendees(self, golden, api_login):
        client = api_login("golden_children_organizer")
        base = f"/persons/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}"
        attendings = client.get(
            f"{base}/assembly_meet_attendings/", {"meets[]": MeetSlugs.THE_ROCK}
        )
        assert attendings.status_code == 200
        attendees = client.get(
            f"{base}/assembly_meet_attendees/", {"meets[]": MeetSlugs.THE_ROCK}
        )
        assert attendees.status_code == 200
        assert attendees.json()["totalCount"] > 10

    def test_data_attendings_are_scoped_to_the_data_division(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            f"/persons/api/{DIVISION_DATA}/{AssemblySlugs.CONGREGATION_DATA}"
            "/data_attendings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE},
        )
        assert response.status_code == 200

    def test_joining_a_meet_through_the_default_endpoint(self, golden, api_login):
        library = Meet.objects.get(slug=MeetSlugs.LIBRARY)
        wilson = golden.attendee("wong_wilson")
        assert not AttendingMeet.objects.filter(
            meet=library, attending__attendee=wilson
        ).exists()
        client = target(api_login("golden_data_organizer"), wilson)
        response = client.put(
            "/persons/api/default_attendingmeets/",
            {"action": "join", "meet": MeetSlugs.LIBRARY},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert AttendingMeet.objects.filter(
            meet=library, attending__attendee=wilson
        ).exists()

    def test_leaving_a_meet_ends_the_participation(self, golden, api_login):
        from attendees.persons.models import Utility

        zhiming = golden.attendee("chen_zhiming")
        client = target(api_login("golden_data_organizer"), zhiming)
        response = client.put(
            "/persons/api/default_attendingmeets/",
            {"action": "leave", "meet": MeetSlugs.DIRECTORY},
            format="json",
        )
        assert response.status_code == 200, response.content
        participation = AttendingMeet.objects.filter(
            meet__slug=MeetSlugs.DIRECTORY, attending__attendee=zhiming
        ).order_by("created").last()
        assert participation.finish <= Utility.now_with_timezone()

    def test_attendings_for_attendance_and_for_attendingmeet_both_answer(
        self, golden, api_login
    ):
        client = api_login("golden_data_organizer")
        for path in (
            "/persons/api/organization_meet_character_attendings_for_attendance/",
            "/persons/api/organization_meet_character_attendings_for_attendingmeet/",
        ):
            response = client.get(path, {"searchValue": "Grace",
                                         "searchExpr": "attendee",
                                         "searchOperation": "contains"})
            assert response.status_code == 200, path


# ------------------------------------------------------------------ lookups
class TestLookupEndpoints:
    def test_categories_can_be_filtered_by_type(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/persons/api/all_categories/", {"type": "folk"})
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert {"Family", "Other", "Carpool"} <= names

    def test_relations_hide_the_internal_hidden_role(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/persons/api/all_relations/",
            {"category_id": FolkCategory.FAMILY, "take": 100},
        )
        assert response.status_code == 200
        titles = {row["title"] for row in response.json()["data"]}
        assert "hidden" not in titles
        assert {"father", "mother", "son", "daughter", "ward"} <= titles

    def test_a_non_counselor_only_sees_the_driver_relation_outside_families(
        self, golden, api_login
    ):
        client = api_login("golden_member")
        response = client.get(
            "/persons/api/all_relations/", {"category_id": FolkCategory.OTHER}
        )
        assert {row["title"] for row in response.json()["data"]} == {"driver"}

    def test_a_counselor_sees_every_relation(self, golden, api_login):
        client = api_login("golden_counselor")
        response = client.get(
            "/persons/api/all_relations/",
            {"category_id": FolkCategory.OTHER, "take": 100},
        )
        titles = {row["title"] for row in response.json()["data"]}
        assert {"guardian", "caregiver", "ex spouse", "neighbor"} <= titles

    def test_registrations_are_listed_for_the_retreat(self, golden, api_login):
        from attendees.occasions.models import Assembly

        assembly = Assembly.objects.get(slug=AssemblySlugs.SUMMER_RETREAT)
        registration = golden.registrations["HH_CHEN_THREE_GEN"]
        client = api_login("golden_conference_organizer")
        response = client.get(
            "/persons/api/all_registrations/",
            {"assembly": assembly.pk, "registrant": str(registration.registrant_id)},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] == 1
        assert response.json()["data"][0]["infos"]["apply_key"]

        by_id = client.get(f"/persons/api/all_registrations/{registration.pk}/")
        assert by_id.status_code == 200
        assert by_id.json()["id"] == registration.pk


# -------------------------------------------------------------------- writes
class TestWrites:
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

    def test_a_family_can_be_created_and_joined(self, golden, api_login):
        wilson = golden.attendee("wong_wilson")
        client = target(api_login("golden_data_organizer"), wilson)
        response = client.post(
            "/persons/api/attendee_families/",
            {
                "category": FolkCategory.OTHER,
                "division": 2,
                "display_name": "Wong small group",
                "infos": {"print_directory": False},
            },
            format="json",
        )
        assert response.status_code in (200, 201), response.content
        assert Folk.objects.filter(display_name="Wong small group").exists()
