import pytest
from datetime import datetime, timedelta, timezone
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from attendees.occasions.models import Assembly, Character, Meet
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    Folk,
    FolkAttendee,
    Relation,
)
from attendees.persons.models.enum import GenderEnum
from attendees.persons.services.attendee_service import AttendeeService
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization


@pytest.mark.django_db
class TestApiSearchAttendeesForRoster:
    def setup_method(self):
        self.org_infos = {
            "groups_see_all_meets_attendees": ["Coworkers"],
            "grade_converter": ["Under three", "Preschool", "Kindergarten", "G1", "G2", "G3", "G4"],
            "settings": {"opencc_convert": True},
        }
        self.organization = Organization.objects.create(
            display_name="First Church",
            slug="first-church",
            infos=self.org_infos,
        )
        self.other_organization = Organization.objects.create(
            display_name="Other Church",
            slug="other-church",
        )
        self.coworker_group = Group.objects.create(name="Coworkers")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Main Division",
            slug="main-division",
            audience_auth_group=self.coworker_group,
        )
        self.other_division = Division.objects.create(
            organization=self.other_organization,
            display_name="Other Division",
            slug="other-division",
            audience_auth_group=self.coworker_group,
        )
        self.family_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "Family", "type": "folk"})
        self.other_cat, _ = Category.objects.get_or_create(id=25, defaults={"display_name": "Other", "type": "folk"})
        self.paused_cat, _ = Category.objects.get_or_create(id=27, defaults={"display_name": "Paused", "type": "attendingmeet"})
        self.scheduled_cat, _ = Category.objects.get_or_create(id=1, defaults={"display_name": "Scheduled", "type": "attendingmeet"})

        self.relation_default, _ = Relation.objects.get_or_create(
            id=0,
            defaults={"title": "test", "gender": GenderEnum.UNSPECIFIED.value}
        )
        self.relation_parent, _ = Relation.objects.get_or_create(
            id=1,
            defaults={"title": "parent", "gender": GenderEnum.UNSPECIFIED.value, "emergency_contact": True}
        )
        self.relation_child, _ = Relation.objects.get_or_create(
            id=2,
            defaults={"title": "child", "gender": GenderEnum.UNSPECIFIED.value}
        )

        self.assembly = Assembly.objects.create(
            display_name="Main Assembly",
            slug="main-assembly",
            division=self.division,
            category=self.other_cat,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Student",
            slug="student",
        )
        self.now = datetime.now(timezone.utc)
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.kid_meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            display_name="Sunday School",
            slug="sunday-school",
            start=self.now,
            finish=self.now + timedelta(days=365),
            site_type=self.site_type,
            site_id=str(self.assembly.id),
            infos={"kid_search_families_show_grades": True},
        )
        self.adult_meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            display_name="Adult Worship",
            slug="adult-worship",
            start=self.now,
            finish=self.now + timedelta(days=365),
            site_type=self.site_type,
            site_id=str(self.assembly.id),
            infos={"kid_search_families_show_grades": False},
        )
        other_assembly = Assembly.objects.create(
            display_name="Other Assembly",
            slug="other-assembly",
            division=self.other_division,
            category=self.other_cat,
        )
        self.other_meet = Meet.objects.create(
            assembly=other_assembly,
            major_character=self.character,
            display_name="Foreign Meet",
            slug="foreign-meet",
            start=self.now,
            finish=self.now + timedelta(days=365),
            site_type=self.site_type,
            site_id=str(other_assembly.id),
        )

        # Users: admin (can see all) and restricted (cannot see all)
        self.admin_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            organization=self.organization,
        )
        self.admin_user.groups.add(self.coworker_group)

        self.restricted_user = User.objects.create_user(
            username="restricteduser",
            email="restricted@example.com",
            organization=self.organization,
        )
        self.restricted_attendee = Attendee.objects.create(
            division=self.division,
            first_name="Restricted",
            last_name="User",
            gender=GenderEnum.UNSPECIFIED.value,
            user=self.restricted_user,
        )

        # Test attendees: Parent & Child sharing a Folk
        self.parent_attendee = Attendee.objects.create(
            division=self.division,
            first_name="Peter",
            last_name="Pan",
            gender=GenderEnum.UNSPECIFIED.value,
            infos={
                "names": {"original": "Peter Pan 潘彼得"},
                "contacts": {
                    "phone1": "+15105551234",
                    "phone3": "+19876543210",
                    "email2": "peter.pan@neverland.org",
                    "wechat1": "peterpan888",
                },
            },
        )
        self.child_attendee = Attendee.objects.create(
            division=self.division,
            first_name="Wendy",
            last_name="Pan",
            first_name2="溫蒂",
            last_name2="潘",
            gender=GenderEnum.UNSPECIFIED.value,
            actual_birthday=self.now.date().replace(year=self.now.year - 8),
            infos={
                "fixed": {"grade": 4},  # index 4 -> "G2" in grade_converter
            },
        )
        self.child_attendee.infos["names"]["nick"] = "Little Wendy"
        self.child_attendee.save()
        self.family_folk = Folk.objects.create(
            division=self.division,
            category=self.family_category,
            display_name="Pan Family",
        )
        FolkAttendee.objects.create(
            folk=self.family_folk,
            attendee=self.parent_attendee,
            role=self.relation_parent,
        )
        FolkAttendee.objects.create(
            folk=self.family_folk,
            attendee=self.child_attendee,
            role=self.relation_child,
        )

        # Restricted user's family
        self.restricted_family = Folk.objects.create(
            division=self.division,
            category=self.family_category,
            display_name="Restricted Family",
        )
        FolkAttendee.objects.create(
            folk=self.restricted_family,
            attendee=self.restricted_attendee,
            role=self.relation_parent,
        )
        self.restricted_child = Attendee.objects.create(
            division=self.division,
            first_name="ChildOf",
            last_name="Restricted",
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"names": {"original": "ChildOf Restricted"}},
        )
        FolkAttendee.objects.create(
            folk=self.restricted_family,
            attendee=self.restricted_child,
            role=self.relation_child,
        )

        self.client = APIClient()

    def test_missing_meet_slug_returns_bad_request(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/persons/api/search_attendees_for_roster/?q=Peter")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_meet_not_found_returns_404(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/persons/api/search_attendees_for_roster/?meet_slug=nonexistent&q=Peter")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_organization_mismatch_returns_403(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.other_meet.slug}&q=Peter")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_empty_query_returns_empty_list(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_full_org_search_when_can_see_all(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=Peter")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        names = [item["name"] for item in data]
        assert any("Peter" in n for n in names)

    def test_restricted_search_when_cannot_see_all(self):
        self.client.force_login(self.restricted_user)
        # Search for Pan (outside restricted user's folks) -> returns empty
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=Pan")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

        # Search for Restricted child (inside restricted user's folks) -> found
        response2 = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=ChildOf")
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert len(data2) >= 1
        assert "ChildOf" in data2[0]["name"]

    def test_phone_search_last_4_digits_and_masking(self):
        self.client.force_login(self.admin_user)
        # Search phone1 last 4 digits
        response1 = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=1234")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert len(data1) >= 1
        peter = next(item for item in data1 if "Peter" in item["name"])
        assert peter["masked_phone"] == "***-**34"

        # Search phone3 last 4 digits
        response3 = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=3210")
        assert response3.status_code == status.HTTP_200_OK
        data3 = response3.json()
        assert any("Peter" in item["name"] for item in data3)

        # Search phone3 with formatting +1(987)654-3210
        response_fmt = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=+1(987)654-3210")
        assert response_fmt.status_code == status.HTTP_200_OK
        data_fmt = response_fmt.json()
        assert any("Peter" in item["name"] for item in data_fmt)

    def test_arbitrary_contacts_search_email_and_wechat(self):
        self.client.force_login(self.admin_user)
        # 1. Search by email domain/part in email2
        response_email = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=neverland.org")
        assert response_email.status_code == status.HTTP_200_OK
        assert any("Peter" in item["name"] for item in response_email.json())

        # 2. Search by WeChat ID in wechat1
        response_wechat = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=peterpan888")
        assert response_wechat.status_code == status.HTTP_200_OK
        assert any("Peter" in item["name"] for item in response_wechat.json())

        # 3. Searching key names like 'wechat' or 'phone' does not false-positive match keys
        response_key = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=wechat")
        assert response_key.status_code == status.HTTP_200_OK
        assert len(response_key.json()) == 0

    def test_fuzzy_trigram_and_chinese_search(self):
        self.client.force_login(self.admin_user)
        # 1. Search using traditional Chinese
        response_trad = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=潘溫蒂")
        assert response_trad.status_code == status.HTTP_200_OK
        data_trad = response_trad.json()
        assert any("Wendy" in item["name"] for item in data_trad)

        # 2. Search using simplified Chinese (precomputed into infos.names.simplified upon save)
        response_simp = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=潘温蒂")
        assert response_simp.status_code == status.HTTP_200_OK
        data_simp = response_simp.json()
        assert any("Wendy" in item["name"] for item in data_simp)

        # 3. Search using nickname
        response_nick = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=Little Wendy")
        assert response_nick.status_code == status.HTTP_200_OK
        data_nick = response_nick.json()
        assert any("Wendy" in item["name"] for item in data_nick)

        # 4. Search with typo using trigram similarity
        response_typo = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=Wandy")
        assert response_typo.status_code == status.HTTP_200_OK
        data_typo = response_typo.json()
        assert any("Wendy" in item["name"] for item in data_typo)

    def test_kid_meet_cross_relation_and_grades(self):
        self.client.force_login(self.admin_user)
        # When searching Peter (the parent) in kid_meet, Wendy (the child) is discovered via cross-relation!
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=Peter")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        wendy = next((item for item in data if "Wendy" in item["name"]), None)
        assert wendy is not None
        assert wendy["matched_by"] == "relation"
        assert "Peter Pan" in wendy["relation_source_name"]
        assert wendy["age"] == 8
        assert wendy["grade_name"] == "G2"  # index 4 mapped via grade_converter
        assert wendy["grade_index"] == 4

    def test_adult_meet_omits_age_grade_and_cross_relation(self):
        self.client.force_login(self.admin_user)
        # When searching Peter in adult_meet, Wendy is NOT included via cross-relation, and age/grade are omitted
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.adult_meet.slug}&q=Peter")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        names = [item["name"] for item in data]
        assert not any("Wendy" in n for n in names)
        peter = data[0]
        assert peter["age"] is None
        assert peter["grade_name"] is None

    def test_meet_status_and_can_join(self):
        self.client.force_login(self.admin_user)

        # 1. Not enrolled
        res1 = AttendeeService.search_for_roster(self.admin_user, self.kid_meet.slug, "Wendy")
        assert res1[0]["meet_status"] == "not_enrolled"
        assert res1[0]["can_join"] is True

        # 2. Enrolled (active)
        attending = Attending.objects.create(attendee=self.child_attendee)
        am = AttendingMeet.objects.create(
            attending=attending,
            meet=self.kid_meet,
            character=self.character,
            category=self.scheduled_cat,
            start=self.now,
            finish=self.now + timedelta(days=30),
        )
        res2 = AttendeeService.search_for_roster(self.admin_user, self.kid_meet.slug, "Wendy")
        assert res2[0]["meet_status"] == "enrolled"
        assert res2[0]["can_join"] is False

        # 3. Paused (category_id == PAUSED_CATEGORY) -> CANNOT join
        am.category = self.paused_cat
        am.save()
        res3 = AttendeeService.search_for_roster(self.admin_user, self.kid_meet.slug, "Wendy")
        assert res3[0]["meet_status"] == "paused"
        assert res3[0]["can_join"] is False

        # 4. Expired -> can join/renew
        am.category = self.scheduled_cat
        am.finish = self.now - timedelta(days=1)
        am.save()
        res4 = AttendeeService.search_for_roster(self.admin_user, self.kid_meet.slug, "Wendy")
        assert res4[0]["meet_status"] == "expired"
        assert res4[0]["can_join"] is True

    def test_folks_array_serialization(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(f"/persons/api/search_attendees_for_roster/?meet_slug={self.kid_meet.slug}&q=Wendy")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        wendy = next(item for item in data if "Wendy" in item["name"])
        assert len(wendy["folks"]) >= 1
        pan_family_folk = next(item for item in wendy["folks"] if item["name"] == "Pan Family")
        assert "id" in pan_family_folk
        assert pan_family_folk["category_id"] == 0
        assert pan_family_folk["role_title"] == "child"
