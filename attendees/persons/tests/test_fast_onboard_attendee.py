from datetime import date, datetime, timedelta, timezone

import pytest
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from attendees.occasions.models import Assembly, Attendance, Character, Gathering, Meet
from attendees.persons.models import Attendee, AttendingMeet, Category, Folk, FolkAttendee, Relation
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization


@pytest.mark.django_db
class TestFastOnboardAttendee:
    def setup_method(self):
        self.client = APIClient()
        self.group = Group.objects.create(name="Test Group")
        self.coworker_group = Group.objects.create(name="attendance_coworkers")

        self.org = Organization.objects.create(
            display_name="Test Church",
            infos={
                "grade_converter": [
                    "Nursery", "Pre-K", "Kindergarten",
                    "1st Grade", "2nd Grade", "3rd Grade",
                    "4th Grade", "5th Grade", "6th Grade",
                    "7th Grade", "8th Grade", "9th Grade",
                    "10th Grade", "11th Grade", "12th Grade",
                ]
            },
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            organization=self.org,
        )
        self.user.groups.add(self.coworker_group)
        self.client.force_login(self.user)

        self.kid_division = Division.objects.create(
            display_name="Children Ministry",
            slug="children-ministry",
            organization=self.org,
            audience_auth_group=self.group,
            infos={"show_attendee_infos": {"infos-grade": True, "infos-insurer": True}},
        )
        self.adult_division = Division.objects.create(
            display_name="Adult Ministry",
            slug="adult-ministry",
            organization=self.org,
            audience_auth_group=self.group,
            infos={"show_attendee_infos": {}},
        )

        self.family_cat, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "Family", "type": "folk"})
        self.other_cat, _ = Category.objects.get_or_create(id=25, defaults={"display_name": "Other", "type": "folk"})
        self.scheduled_cat, _ = Category.objects.get_or_create(id=1, defaults={"display_name": "Scheduled", "type": "attendingmeet"})
        self.attended_cat, _ = Category.objects.get_or_create(
            id=Attendee.ATTENDED_CATEGORY,
            defaults={"display_name": "attended", "type": "attendance"}
        )

        self.relation_default, _ = Relation.objects.get_or_create(
            id=0,
            defaults={"title": "unspecified", "gender": "unspecified"}
        )
        self.relation_parent, _ = Relation.objects.get_or_create(
            id=1,
            defaults={"title": "parent", "gender": "unspecified", "emergency_contact": True, "consanguinity": True, "relative": True}
        )
        self.relation_child, _ = Relation.objects.get_or_create(
            id=2,
            defaults={"title": "child", "gender": "unspecified", "consanguinity": True, "relative": True}
        )

        # Assemblies
        self.kid_assembly = Assembly.objects.create(
            display_name="Children Assembly",
            slug="children-assembly",
            division=self.kid_division,
            category=self.other_cat,
        )
        self.adult_assembly = Assembly.objects.create(
            display_name="Adult Assembly",
            slug="adult-assembly",
            division=self.adult_division,
            category=self.other_cat,
        )

        # Characters
        self.kid_character = Character.objects.create(
            assembly=self.kid_assembly,
            display_name="Student",
            slug="kid-student",
            display_order=1,
            type="normal",
        )
        self.adult_character = Character.objects.create(
            assembly=self.adult_assembly,
            display_name="Participant",
            slug="adult-participant",
            display_order=1,
            type="normal",
        )

        # Meets
        now = datetime.now(timezone.utc)
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.kid_meet = Meet.objects.create(
            assembly=self.kid_assembly,
            major_character=self.kid_character,
            shown_audience=True,
            audience_editable=True,
            start=now - timedelta(days=1),
            finish=now + timedelta(days=365),
            display_name="Kindergarten Sunday School",
            slug="kindergarten-sunday-school",
            infos={"kid_search_families_show_grades": True},
            site_type=self.site_type,
            site_id=str(self.kid_assembly.id),
        )
        self.adult_meet = Meet.objects.create(
            assembly=self.adult_assembly,
            major_character=self.adult_character,
            shown_audience=True,
            audience_editable=True,
            start=now - timedelta(days=1),
            finish=now + timedelta(days=365),
            display_name="English Fellowship",
            slug="english-fellowship",
            infos={},
            site_type=self.site_type,
            site_id=str(self.adult_assembly.id),
        )

        # Gathering
        self.kid_gathering = Gathering.objects.create(
            meet=self.kid_meet,
            start=now,
            finish=now + timedelta(hours=2),
            display_name="Sunday Service Gathering",
            site_type=self.site_type,
            site_id=str(self.kid_assembly.id),
        )

    def test_kid_fast_onboard_with_parent_and_attendance(self):
        payload = {
            "meet_slug": self.kid_meet.slug,
            "gathering_id": self.kid_gathering.id,
            "kid_data": {
                "first_name": "Peter",
                "last_name": "Pan",
                "first_name2": "彼得",
                "last_name2": "潘",
                "gender": "male",
                "birthday_year": 2018,
                "birthday_month": 5,
                "birthday_day": 20,
                "grade": 2,  # Kindergarten index
                "food_pref": "Peanut allergy",
                "insurer": "Kaiser Permanente",
            },
            "parent_data": {
                "first_name": "Mary",
                "last_name": "Pan",
                "first_name2": "瑪麗",
                "last_name2": "潘",
                "gender": "female",
                "phone": "510-555-0199",
                "email": "mary@pan.org",
                "relationship": "parent",
            },
            "unaccompanied": False,
        }

        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        data = response.data
        assert data["first_name"] == "Peter"
        assert data["last_name"] == "Pan"
        assert data["first_name2"] == "彼得"
        assert data["last_name2"] == "潘"
        assert data["actual_birthday"] == "2018-05-20"
        assert data["estimated_birthday"] is None
        assert data["warning"] is None
        assert data["attendance_id"] is not None

        # Verify kid Attendee DB record
        kid = Attendee.objects.get(id=data["attendee_id"])
        assert kid.actual_birthday == date(2018, 5, 20)
        assert kid.infos["fixed"]["grade"] == 2
        assert kid.infos["fixed"]["food_pref"] == "Peanut allergy"
        assert kid.infos["fixed"]["insurer"] == "Kaiser Permanente"

        # Verify parent DB record
        parent = Attendee.objects.get(id=data["parent_id"])
        assert parent.first_name == "Mary"
        assert parent.last_name == "Pan"
        assert parent.infos["contacts"]["phone"] == "510-555-0199"
        assert parent.infos["contacts"]["email"] == "mary@pan.org"

        # Verify family folk & FolkAttendee links
        family = Folk.objects.filter(attendees=kid, category_id=Attendee.FAMILY_CATEGORY).first()
        assert family is not None
        assert "Pan family" in family.display_name
        assert FolkAttendee.objects.filter(folk=family, attendee=kid, role=self.relation_child).exists()
        assert FolkAttendee.objects.filter(folk=family, attendee=parent, role=self.relation_parent).exists()

        # Verify Attendance record
        attendance = Attendance.objects.get(id=data["attendance_id"])
        assert attendance.gathering == self.kid_gathering
        assert attendance.attending == kid.attendings.first()
        assert attendance.category_id == Attendee.ATTENDED_CATEGORY

    def test_kid_fast_onboard_unaccompanied_minor(self):
        payload = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Oliver",
                "last_name": "Twist",
                "birthday_year": 2017,
                "birthday_month": 3,
                "birthday_day": 15,
                "grade": 1,
                "food_pref": "None",
            },
            "unaccompanied": True,
        }

        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        data = response.data
        assert data["warning"] == "⚠Missing companion info"
        assert data["parent_id"] is None

        am = AttendingMeet.objects.get(id=data["attendingmeet_id"])
        assert am.infos["special"]["check_in"] == "⚠Missing companion info"

    def test_auto_clear_unaccompanied_warning_when_parent_linked(self):
        # 1. Onboard unaccompanied kid
        payload = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Timmy",
                "last_name": "Brown",
                "birthday_year": 2016,
                "birthday_month": 8,
                "birthday_day": 10,
                "grade": 3,
                "food_pref": "None",
            },
            "unaccompanied": True,
        }
        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        kid_id = response.data["attendee_id"]
        am_id = response.data["attendingmeet_id"]

        am = AttendingMeet.objects.get(id=am_id)
        assert am.infos["special"]["check_in"] == "⚠Missing companion info"

        # 2. Later, parent arrives and is linked to the kid in a family folk
        kid = Attendee.objects.get(id=kid_id)
        parent = Attendee.objects.create(
            first_name="David",
            last_name="Brown",
            gender="male",
            division=self.kid_division,
            infos={"contacts": {"phone": "510-555-9988"}},
        )
        family = Folk.objects.create(
            category=self.family_cat,
            division=self.kid_division,
            display_name="Brown family",
        )
        FolkAttendee.objects.create(
            folk=family,
            attendee=kid,
            role=self.relation_child,
        )

        # Saving parent's FolkAttendee triggers the post_save receiver
        FolkAttendee.objects.create(
            folk=family,
            attendee=parent,
            role=self.relation_parent,
        )

        # 3. Verify that the warning flag in attendingmeet was automatically cleared
        am.refresh_from_db()
        assert "special" not in (am.infos or {}) or "check_in" not in am.infos.get("special", {})

    def test_adult_fast_onboard_partial_birthday(self):
        # Yearless birthday (only month and day given)
        payload = {
            "meet_slug": self.adult_meet.slug,
            "kid_data": {
                "first_name": "Elder",
                "last_name": "Wang",
                "birthday_month": 12,
                "birthday_day": 25,
            },
            "unaccompanied": False,
        }

        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        data = response.data
        assert data["actual_birthday"] is None
        assert data["estimated_birthday"] == "1800-12-25"
        assert data["warning"] is None

        attendee = Attendee.objects.get(id=data["attendee_id"])
        assert attendee.estimated_birthday is not None
        assert str(attendee.estimated_birthday) == "1800-12-25"

    def test_kid_fast_onboard_missing_required_fields(self):
        # Missing birthday year
        payload = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Baby",
                "last_name": "Doe",
                "birthday_month": 5,
                "birthday_day": 10,
                "grade": 0,
                "food_pref": "Milk",
            },
            "unaccompanied": True,
        }
        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "birthday" in response.data

        # Missing grade
        payload2 = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Baby",
                "last_name": "Doe",
                "birthday_year": 2020,
                "birthday_month": 5,
                "birthday_day": 10,
                "food_pref": "Milk",
            },
            "unaccompanied": True,
        }
        response2 = self.client.post("/persons/api/fast_onboard_attendee/", payload2, format="json")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "grade" in response2.data

        # Missing food_pref
        payload3 = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Baby",
                "last_name": "Doe",
                "birthday_year": 2020,
                "birthday_month": 5,
                "birthday_day": 10,
                "grade": 0,
            },
            "unaccompanied": True,
        }
        response3 = self.client.post("/persons/api/fast_onboard_attendee/", payload3, format="json")
        assert response3.status_code == status.HTTP_400_BAD_REQUEST
        assert "food_pref" in response3.data

        # Not unaccompanied and missing parent
        payload4 = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Baby",
                "last_name": "Doe",
                "birthday_year": 2020,
                "birthday_month": 5,
                "birthday_day": 10,
                "grade": 0,
                "food_pref": "None",
            },
            "unaccompanied": False,
        }
        response4 = self.client.post("/persons/api/fast_onboard_attendee/", payload4, format="json")
        assert response4.status_code == status.HTTP_400_BAD_REQUEST
        assert "unaccompanied" in response4.data

    def test_single_name_allowed(self):
        # Kid with only first_name
        payload = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Prince",
                "birthday_year": 2018,
                "birthday_month": 1,
                "birthday_day": 1,
                "grade": 1,
                "food_pref": "None",
            },
            "unaccompanied": True,
        }
        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["first_name"] == "Prince"
        assert response.data["last_name"] is None

        # Kid with only last_name2
        payload2 = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "last_name2": "王",
                "birthday_year": 2018,
                "birthday_month": 1,
                "birthday_day": 1,
                "grade": 1,
                "food_pref": "None",
            },
            "unaccompanied": True,
        }
        response2 = self.client.post("/persons/api/fast_onboard_attendee/", payload2, format="json")
        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.data["last_name2"] == "王"

    def test_custom_relationship_assignment(self):
        guardian_rel, _ = Relation.objects.get_or_create(
            id=15,
            defaults={"title": "guardian", "gender": "unspecified", "reciprocal_ids": [16]}
        )
        ward_rel, _ = Relation.objects.get_or_create(
            id=16,
            defaults={"title": "ward", "gender": "unspecified", "reciprocal_ids": [15]}
        )

        payload = {
            "meet_slug": self.kid_meet.slug,
            "kid_data": {
                "first_name": "Oliver",
                "last_name": "Twist",
                "birthday_year": 2017,
                "birthday_month": 3,
                "birthday_day": 15,
                "grade": 2,
                "food_pref": "None",
            },
            "parent_data": {
                "first_name": "John",
                "last_name": "Brown",
                "phone": "555-1234",
                "division_id": self.adult_division.id,
                "relationship": guardian_rel.id,
            },
            "unaccompanied": False,
        }
        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        kid_id = response.data["attendee_id"]
        parent_id = response.data["parent_id"]

        # Guardian is non-consanguinity, so it should be linked in NON_FAMILY_CATEGORY (category 25)
        # without creating duplicate folks
        assert Folk.objects.filter(attendees=kid_id, category_id=Attendee.NON_FAMILY_CATEGORY).count() == 1

        parent_fa = FolkAttendee.objects.filter(folk__category_id=Attendee.NON_FAMILY_CATEGORY, attendee_id=parent_id, role=guardian_rel).first()
        child_fa = FolkAttendee.objects.filter(folk__category_id=Attendee.NON_FAMILY_CATEGORY, attendee_id=kid_id, role=ward_rel).first()

        assert parent_fa is not None
        assert parent_fa.role.id == guardian_rel.id
        assert parent_fa.role.title == "guardian"

        assert child_fa is not None
        assert child_fa.role.id == ward_rel.id
        assert child_fa.role.title == "ward"

    def test_multiple_companions_and_gathering_occurrence(self):
        guardian_rel, _ = Relation.objects.get_or_create(
            id=15,
            defaults={"title": "guardian", "gender": "unspecified", "reciprocal_ids": [16], "consanguinity": False}
        )
        ward_rel, _ = Relation.objects.get_or_create(
            id=16,
            defaults={"title": "ward", "gender": "unspecified", "reciprocal_ids": [15], "consanguinity": False}
        )

        meeting_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        occurrence_str = f"start_{meeting_time.isoformat()}"

        payload = {
            "meet_slug": self.kid_meet.slug,
            "gathering_id": occurrence_str,
            "unaccompanied": False,
            "kid_data": {
                "first_name": "Alice",
                "last_name": "Wonderland",
                "birthday_year": 2017,
                "birthday_month": 5,
                "birthday_day": 20,
                "contact_type": "phone",
                "contact_value": "408-111-2222",
                "grade": 2,
                "food_pref": "No peanuts",
            },
            "companions": [
                {
                    "first_name": "Mary",
                    "last_name": "Wonderland",
                    "division_id": self.adult_division.id,
                    "relationship": self.relation_parent.id,
                    "contact_type": "phone",
                    "contact_value": "408-333-4444",
                },
                {
                    "first_name": "Grandpa",
                    "last_name": "Joe",
                    "division_id": self.adult_division.id,
                    "relationship": guardian_rel.id,
                    "contact_type": "wechat",
                    "contact_value": "grandpajoe_wechat",
                },
            ],
        }

        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        kid_id = response.data["attendee_id"]
        companion_ids = response.data["companion_ids"]
        assert len(companion_ids) == 2

        comp1 = Attendee.objects.get(pk=companion_ids[0])
        comp2 = Attendee.objects.get(pk=companion_ids[1])
        assert comp1.first_name == "Mary"
        assert comp1.infos["contacts"]["phone1"] == "408-333-4444"
        assert comp2.first_name == "Grandpa"
        assert comp2.infos["contacts"]["wechat1"] == "grandpajoe_wechat"

        # Check emergency contacts in kid.infos
        kid = Attendee.objects.get(pk=kid_id)
        emergency_contacts = kid.infos.get("emergency_contacts", {})
        assert len(emergency_contacts) == 2
        assert str(comp1.id) in emergency_contacts
        assert str(comp2.id) in emergency_contacts

        # Family folk (Category 0) has kid + Mary
        family_folk = Folk.objects.filter(attendees=kid_id, category_id=Attendee.FAMILY_CATEGORY).first()
        assert family_folk is not None
        assert comp1 in family_folk.attendees.all()
        assert comp2 not in family_folk.attendees.all()

        # Non-family folk (Category 25) has kid + Grandpa
        non_family_folk = Folk.objects.filter(attendees=kid_id, category_id=Attendee.NON_FAMILY_CATEGORY).first()
        assert non_family_folk is not None
        assert comp2 in non_family_folk.attendees.all()

        # Gathering was auto-created and attended
        assert response.data["gathering_id"] is not None
        gathering = Gathering.objects.get(pk=response.data["gathering_id"])
        assert gathering.meet == self.kid_meet
        attendance = Attendance.objects.filter(gathering=gathering, attending__attendee=kid).first()
        assert attendance is not None

    def test_adult_fast_onboard_with_companion(self):
        spouse_rel, _ = Relation.objects.get_or_create(
            id=3,
            defaults={"title": "spouse", "gender": "unspecified", "reciprocal_ids": [3], "consanguinity": False, "relative": True}
        )

        payload = {
            "meet_slug": self.adult_meet.slug,
            "unaccompanied": False,
            "kid_data": {
                "first_name": "David",
                "last_name": "Smith",
                "birthday_year": 1985,
                "birthday_month": 8,
                "birthday_day": 10,
                "contact_type": "phone",
                "contact_value": "408-555-1111",
            },
            "companions": [
                {
                    "first_name": "Sarah",
                    "last_name": "Smith",
                    "division_id": self.adult_division.id,
                    "relationship": spouse_rel.id,
                    "contact_type": "email",
                    "contact_value": "sarah@smith.com",
                }
            ],
        }

        response = self.client.post("/persons/api/fast_onboard_attendee/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        adult_id = response.data["attendee_id"]
        companion_ids = response.data["companion_ids"]
        assert len(companion_ids) == 1

        adult = Attendee.objects.get(pk=adult_id)
        comp = Attendee.objects.get(pk=companion_ids[0])
        assert adult.first_name == "David"
        assert comp.first_name == "Sarah"
        assert comp.infos["contacts"]["email1"] == "sarah@smith.com"

        # Check family folk has both David and Sarah
        family_folk = Folk.objects.filter(attendees=adult_id, category_id=Attendee.FAMILY_CATEGORY).first()
        assert family_folk is not None
        assert comp in family_folk.attendees.all()


