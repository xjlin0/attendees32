"""Every ``/occasions/api/…`` endpoint: meets, characters, teams, gatherings,
attendances, statistics and calendars."""

from datetime import timedelta

import pytest

from attendees.occasions.models import Assembly, Attendance, Gathering, Meet
from attendees.persons.models import Attending, Utility
from attendees.tests.golden.constants import (
    AssemblySlugs,
    AttendanceCategory,
    DIVISION_SLUGS,
    MeetSlugs,
)

pytestmark = pytest.mark.django_db

DIVISION_JUNIOR = DIVISION_SLUGS[3]
DIVISION_DATA = DIVISION_SLUGS[5]
JUNIOR_STUDENT_SLUG = "d7c8Fd_cfcch_kid_student"
CONGREGATION_SLUG = "d7c8Fd_cfcch_congregation_data_roster"


def window():
    now = Utility.now_with_timezone()
    return {
        "start": (now - timedelta(weeks=12)).isoformat(),
        "finish": (now + timedelta(weeks=2)).isoformat(),
    }


# -------------------------------------------------------------- the vocabulary
class TestOrganizationVocabulary:
    def test_assemblies_are_listed_for_the_users_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/user_assemblies/", {"take": 100})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert AssemblySlugs.CONGREGATION_DATA in slugs
        assert AssemblySlugs.CROSSING_YOUTH in slugs  # added by the golden builder
        assert "heaven_throne_worship" not in slugs  # a different organization

    def test_assemblies_can_be_searched(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/user_assemblies/",
            {"searchValue": "Youth", "searchExpr": "display_name",
             "searchOperation": "contains"},
        )
        assert {row["slug"] for row in response.json()["data"]} == {
            AssemblySlugs.CROSSING_YOUTH
        }

    def test_an_account_without_an_organization_is_refused(self, golden, api_login):
        client = api_login("golden_outsider")
        assert client.get("/occasions/api/user_assemblies/").status_code == 403

    def test_meets_are_listed_by_slug(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_meets/", {"take": 100})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {MeetSlugs.CHINESE_SERVICE, MeetSlugs.ENGLISH_SERVICE,
                MeetSlugs.THE_ROCK} <= slugs

    def test_characters_are_listed_for_the_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_characters/", {"take": 200})
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert JUNIOR_STUDENT_SLUG in slugs
        assert "golden_youth_student" in slugs

    def test_characters_can_be_scoped_to_an_assembly(self, golden, api_login):
        junior = Assembly.objects.get(slug=AssemblySlugs.JUNIOR_REGULAR)
        client = api_login("golden_data_organizer")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get(
            "/occasions/api/user_assembly_characters/",
            {"assemblies[]": junior.pk, "take": 100},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 5

    def test_meets_can_be_scoped_to_an_assembly(self, golden, api_login):
        junior = Assembly.objects.get(slug=AssemblySlugs.JUNIOR_REGULAR)
        client = api_login("golden_data_organizer")
        client.credentials(
            HTTP_X_TARGET_ATTENDEE_ID=str(golden.attendee("chen_joshua").id)
        )
        response = client.get(
            "/occasions/api/user_assembly_meets/",
            {"assemblies[]": junior.pk, "take": 100},
        )
        assert response.status_code == 200
        slugs = {row["slug"] for row in response.json()["data"]}
        assert {MeetSlugs.THE_ROCK, MeetSlugs.LITTLE_FOOT} <= slugs

    def test_the_target_attendees_own_meets_lead_the_first_page(
        self, golden, api_login
    ):
        """The attendee page's participation grid resolves meet names from
        the first page of this endpoint only, so the attendee's own meets
        must sort ahead of everyone else's -- or her rows show blank."""
        grace = golden.attendee("chen_grace")
        client = api_login("golden_data_organizer")
        client.credentials(HTTP_X_TARGET_ATTENDEE_ID=str(grace.id))
        response = client.get(
            "/occasions/api/user_assembly_meets/",
            {"searchOperation": "contains", "searchValue": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["totalCount"] > len(body["data"])  # it really is paged
        joined = set(
            Meet.objects.filter(attendingmeet__attending__attendee=grace).values_list(
                "slug", flat=True
            )
        )
        first_page = [row["slug"] for row in body["data"]]
        assert joined <= set(first_page)
        assert all(slug in joined for slug in first_page[: len(joined)])

    def test_teams_are_listed_per_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_teams/",
            {"meets[]": MeetSlugs.CHINESE_CHOIR, "take": 100},
        )
        assert response.status_code == 200
        names = {row["display_name"] for row in response.json()["data"]}
        assert {"女高音 soprano", "男低音 bass"} <= names

    def test_assembly_scoped_characters_teams_and_gatherings(self, golden, api_login):
        client = api_login("golden_children_organizer")
        base = f"/occasions/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}"
        for endpoint in ("assembly_meet_characters", "assembly_meet_teams",
                         "assembly_meet_gatherings"):
            response = client.get(
                f"{base}/{endpoint}/", {"meets[]": MeetSlugs.THE_ROCK}
            )
            assert response.status_code == 200, endpoint


# ------------------------------------------------------------------ gatherings
class TestGatherings:
    def test_gatherings_are_listed_for_a_meet(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_team_gatherings/",
            {"meets[]": MeetSlugs.CHINESE_SERVICE, **window(), "take": 50},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] == 8  # eight Sundays of history

    def test_a_family_sees_the_gatherings_of_the_meets_they_joined(
        self, golden, api_login
    ):
        client = api_login("golden_member")
        response = client.get(
            "/occasions/api/family_organization_gatherings/",
            {"meets[]": MeetSlugs.THE_ROCK},
        )
        assert response.status_code == 200

    def test_a_coworker_can_batch_create_gatherings(self, golden, api_login):
        """``series_gatherings`` walks the meet's schedule rules."""
        meet = Meet.objects.get(slug=MeetSlugs.THE_ROCK)
        before = Gathering.objects.filter(meet=meet).count()
        now = Utility.now_with_timezone()
        client = api_login("golden_children_organizer")
        response = client.post(
            "/occasions/api/series_gatherings/",
            {
                "meet_slug": MeetSlugs.THE_ROCK,
                "begin": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=22)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "duration": 75,
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        payload = response.json()
        assert payload["success"] is True
        assert Gathering.objects.filter(meet=meet).count() == (
            before + payload["number_created"]
        )

    def test_batch_creation_is_refused_without_the_right_group(self, golden, api_login):
        client = api_login("golden_member")
        response = client.post(
            "/occasions/api/series_gatherings/",
            {"meet_slug": MeetSlugs.THE_ROCK, "begin": "", "end": "", "duration": 75},
            format="json",
        )
        assert "does not have permissions to visit such route" in response.content.decode()

    def test_batch_creating_attendances_follows_the_gatherings(self, golden, api_login):
        now = Utility.now_with_timezone()
        client = api_login("golden_children_organizer")
        response = client.post(
            "/occasions/api/series_attendances/",
            {
                "meet_slug": MeetSlugs.THE_ROCK,
                "begin": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "duration": 75,
            },
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["gathering_generation_success"] is True


# ----------------------------------------------------------------- attendances
class TestAttendances:
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

    def test_a_coworker_sees_the_organizations_attendances(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            "/occasions/api/coworker_organization_attendances/",
            {"meets[]": MeetSlugs.THE_ROCK, **window(), "take": 10},
        )
        assert response.status_code == 200
        assert response.json()["totalCount"] > 0

    def test_a_parent_sees_only_their_family_attendances(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get(
            "/occasions/api/family_organization_attendances/",
            {
                "meets[]": MeetSlugs.THE_ROCK,
                "attendee": str(golden.attendee("chen_joshua").id),
                **window(),
            },
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert rows, "Joshua has eight weeks of The Rock history"

    def test_family_characters_are_listed(self, golden, api_login):
        client = api_login("golden_member")
        response = client.get("/occasions/api/family_organization_characters/")
        assert response.status_code == 200

    def test_assembly_scoped_attendances(self, golden, api_login):
        client = api_login("golden_children_organizer")
        response = client.get(
            f"/occasions/api/{DIVISION_JUNIOR}/{AssemblySlugs.JUNIOR_REGULAR}"
            "/assembly_meet_attendances/",
            {"meets[]": MeetSlugs.THE_ROCK, "characters[]": JUNIOR_STUDENT_SLUG,
             **window()},
        )
        assert response.status_code == 200

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


# ------------------------------------------------------------------ statistics
class TestStatistics:
    def test_attendance_counts_are_grouped_per_person(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_character_attendance_stats/",
            {
                "meets[]": MeetSlugs.CHINESE_SERVICE,
                "characters[]": CONGREGATION_SLUG,
                "categories[]": AttendanceCategory.ATTENDED,
                **window(),
                "take": 25,
            },
        )
        assert response.status_code == 200
        rows = response.json()["data"]
        assert rows
        assert all(row["count"] >= 1 for row in rows)
        assert max(row["count"] for row in rows) <= 8  # only eight Sundays exist

    def test_statistics_can_be_narrowed_to_one_name(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get(
            "/occasions/api/organization_meet_character_attendance_stats/",
            {
                "meets[]": MeetSlugs.CHINESE_SERVICE,
                "characters[]": CONGREGATION_SLUG,
                **window(),
                "filter": str([["attending_name", "contains", "Zhiming"]]),
            },
        )
        assert response.status_code == 200


# ------------------------------------------------------------------- calendars
class TestCalendars:
    def test_calendars_are_listed_for_the_organization(self, golden, api_login):
        client = api_login("golden_data_organizer")
        response = client.get("/occasions/api/organization_calendars/", {"take": 50})
        assert response.status_code == 200
        assert response.json()["totalCount"] >= 1

    def test_occurrences_need_a_window(self, golden, api_login):
        client = api_login("golden_data_organizer")
        now = Utility.now_with_timezone()
        response = client.get(
            "/occasions/api/organization_occurrences/",
            {
                "start": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "end": (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
                "take": 50,
            },
        )
        assert response.status_code == 200
