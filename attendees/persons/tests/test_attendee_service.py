import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division
from attendees.persons.models import Attendee, Attending, AttendingMeet, Category, Registration, Relation, Folk, FolkAttendee, Past
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Meet, Character, Assembly
from attendees.persons.services.attendee_service import AttendeeService

@pytest.mark.django_db
class TestAttendeeService:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Organization", slug="test-org")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.category_1 = Category.objects.create(id=1, display_name="Scheduled")
        self.family_category = Category.objects.create(id=0, display_name="Family")
        self.past_category = Category.objects.create(id=26, display_name="Past Category")
        self.relation = Relation.objects.create(id=0, title="test relation", gender=GenderEnum.UNSPECIFIED.value)
        
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Character",
            slug="test-character",
            type="normal",
        )
        self.site_type = ContentType.objects.get_for_model(Assembly)
        
        self.now = datetime.now(timezone.utc)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=1),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )

        self.user = User.objects.create(
            username="testuser",
            email="testuser@example.com",
            organization=self.organization
        )

        self.attendee = Attendee.objects.create(
            first_name="John",
            last_name="Doe",
            division=self.division,
            user=self.user,
            gender="unspecified"
        )
        self.user.attendee = self.attendee
        self.user.save()

        self.attending = Attending.objects.filter(attendee=self.attendee).first()
        if not self.attending:
            self.attending = Attending.objects.create(attendee=self.attendee)

        self.attendingmeet = AttendingMeet.objects.create(
            attending=self.attending,
            meet=self.meet,
            character=self.character,
            finish=self.now + timedelta(days=10)
        )

    def test_by_assembly_meets(self):
        qs = AttendeeService.by_assembly_meets(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.attendee.id

    def test_orderby_parser(self):
        orderby_string = '[{"selector":"first_name","desc":true}]'
        # Pass empty list for meets for simplicity
        parsed = AttendeeService.orderby_parser(orderby_string, [], self.user)
        assert len(parsed) == 1
        assert parsed[0] == "-first_name"

    def test_field_convert(self):
        field = AttendeeService.field_convert("self_phone_numbers", [], self.user)
        assert field == "infos__contacts"

    def test_create_or_update_first_folk(self):
        folk = AttendeeService.create_or_update_first_folk(
            attendee=self.attendee,
            folk_name="Doe Family",
            category_id=self.family_category.id,
            role_id=self.relation.id
        )
        assert folk is not None
        assert folk.display_name == "Doe Family"
        assert FolkAttendee.objects.filter(folk=folk, attendee=self.attendee).exists()

    def test_add_past(self):
        AttendeeService.add_past(self.attendee, self.past_category.id, timezone.utc)
        assert Past.objects.filter(object_id=self.attendee.id, category=self.past_category).exists()

    def test_end_all_activities(self):
        # We must add a past first
        AttendeeService.add_past(self.attendee, self.past_category.id, timezone.utc)
        past = Past.objects.filter(object_id=self.attendee.id).first()
        
        AttendeeService.end_all_activities(self.attendee, str(uuid4()))
        
        self.attendingmeet.refresh_from_db()
        past.refresh_from_db()
        assert self.attendingmeet.finish <= datetime.now(timezone.utc)
        assert past.finish <= datetime.now(timezone.utc)

    def test_destroy_with_associations(self):
        # Add past to be sure it's deleted
        AttendeeService.add_past(self.attendee, self.past_category.id, timezone.utc)
        
        assert Attendee.objects.filter(id=self.attendee.id).exists()
        
        AttendeeService.destroy_with_associations(self.attendee)
        
        # Soft deleted
        self.attendee.refresh_from_db()
        assert self.attendee.is_removed is True
        
        # Pasts should be soft-deleted or deleted depending on logic
        assert not Past.objects.filter(object_id=self.attendee.id, is_removed=False).exists()
