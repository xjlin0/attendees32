import pytest
from datetime import datetime, timedelta, timezone
from partial_date import PartialDate
from uuid import uuid4
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group

from attendees.whereabouts.models import Organization, Division
from attendees.occasions.models import Assembly, Character, Meet
from attendees.persons.models import Category, Attendee, Attending, AttendingMeet, Past, Folk, Relation
from attendees.persons.models.enum import GenderEnum

@pytest.mark.django_db
class TestPersonsSignals:
    def setup_method(self):
        self.organization = Organization.objects.create(
            display_name="Test Org", 
            slug="test-org",
            infos={
                "settings": {
                    "past_category_to_attendingmeet_meet": {
                        "26": 1 # we will update this id later
                    },
                    "attendee_to_attending": True
                }
            }
        )
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Div",
            slug="test-div",
            audience_auth_group=self.group
        )
        self.category_1 = Category.objects.create(id=1, display_name="Scheduled")
        self.family_category = Category.objects.create(id=0, display_name="Family")
        self.past_category = Category.objects.create(id=26, display_name="Past Category")
        self.relation = Relation.objects.create(id=0, title="test relation", gender=GenderEnum.UNSPECIFIED.value)
        self.hidden_role = Relation.objects.create(id=8, title="hidden", gender=GenderEnum.UNSPECIFIED.value) # Attendee.HIDDEN_ROLE is usually 8
        self.non_family_category = Category.objects.create(id=25, display_name="Non Family") # Attendee.NON_FAMILY_CATEGORY is usually 25.

        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category_1,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Char",
            slug="test-char",
            type="normal",
        )
        from attendees.whereabouts.models import Room
        self.room = Room.objects.create(display_name="Room A", slug="room-a")
        self.site_type = ContentType.objects.get_for_model(Room)

        self.now = datetime.now(timezone.utc)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=10),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.room.id),
            infos={
                "automatic_modification": {"Folk": True},
                "automatic_creation": {"Past": 26}
            }
        )
        
        # update org infos with real meet id
        self.organization.infos["settings"]["past_category_to_attendingmeet_meet"]["26"] = self.meet.id
        self.organization.save()

    def test_post_save_handler_for_attendee_to_folk_and_attending(self):
        # When creating an attendee, it should auto-create a non-family Folk and an Attending
        attendee = Attendee.objects.create(
            first_name="Jane",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
            infos={"names": {"original": "Jane Doe"}}
        )

        # Check if Attending was created
        assert Attending.objects.filter(attendee=attendee).exists()
        
        # Check if Folk was created
        # Expecting a folk with name "Jane Doe other"
        folks = Folk.objects.filter(display_name="Jane Doe other")
        assert folks.exists()
        assert folks.first().folkattendee_set.filter(attendee=attendee).exists()

    def test_post_save_handler_for_past_to_create_attendingmeet(self):
        attendee = Attendee.objects.create(
            first_name="Jane",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
            infos={"names": {"original": "Jane Doe"}}
        )
        # Ensure Attending is there (should be from previous signal, but just in case)
        if not Attending.objects.filter(attendee=attendee).exists():
            Attending.objects.create(attendee=attendee)
            
        content_type = ContentType.objects.get_for_model(Attendee)
        
        # Creating a Past with category 26 should trigger AttendingMeet creation for self.meet
        past = Past.objects.create(
            organization=self.organization,
            content_type=content_type,
            object_id=attendee.id,
            category=self.past_category,
            display_name="Test Past",
            when="2023-01-01"
        )
        
        # Check if AttendingMeet was created
        assert AttendingMeet.objects.filter(
            attending__attendee=attendee,
            meet=self.meet
        ).exists()

    def test_post_save_handler_for_attendingmeet_to_modify_folk(self):
        attendee = Attendee.objects.create(
            first_name="Jane",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
            infos={"names": {"original": "Jane Doe"}}
        )
        attending = Attending.objects.filter(attendee=attendee).first()
        
        # Create a real family folk
        family_folk = Folk.objects.create(
            division=self.division,
            category=self.family_category,
            display_name="Jane's Family"
        )
        family_folk.folkattendee_set.create(attendee=attendee, role=self.relation)
        
        # Creating AttendingMeet should update the folk's print_directory info
        attendingmeet = AttendingMeet.objects.create(
            attending=attending,
            meet=self.meet,
            character=self.character,
            category=self.category_1, # Scheduled category
            finish=self.now + timedelta(days=10)
        )
        
        family_folk.refresh_from_db()
        assert family_folk.infos.get('print_directory') is True

    def test_post_save_handler_for_attendingmeet_to_create_past(self):
        attendee = Attendee.objects.create(
            first_name="Jane",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
            infos={"names": {"original": "Jane Doe"}}
        )
        attending = Attending.objects.filter(attendee=attendee).first()
        
        # Creating AttendingMeet should also create a Past (since automatic_creation is set in Meet)
        attendingmeet = AttendingMeet.objects.create(
            attending=attending,
            meet=self.meet,
            character=self.character,
            category=self.category_1,
            finish=self.now + timedelta(days=10)
        )
        
        # Check if Past was created
        assert Past.objects.filter(
            object_id=attendee.id,
            category=self.past_category,
            display_name="Please update the date"
        ).exists()
