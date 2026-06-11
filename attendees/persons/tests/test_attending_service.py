import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division
from attendees.persons.models import Attendee, Attending, AttendingMeet, Category, Registration, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Meet, Character, Assembly, Gathering, Attendance
from attendees.persons.services.attending_service import AttendingService

@pytest.mark.django_db
class TestAttendingService:
    def setup_method(self):
        self.relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
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

        # Attendee auto-creates an Attending, let's get it or create one if not auto-created
        self.attending = Attending.objects.filter(attendee=self.attendee).first()
        if not self.attending:
            self.attending = Attending.objects.create(attendee=self.attendee)

        self.registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee
        )
        self.attending.registration = self.registration
        self.attending.save()

        self.attendingmeet = AttendingMeet.objects.create(
            attending=self.attending,
            meet=self.meet,
            character=self.character,
            finish=self.now + timedelta(days=10)
        )

        self.gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )

        self.attendance = Attendance.objects.create(
            gathering=self.gathering,
            attending=self.attending,
            character=self.character,
            start=self.now,
            finish=self.now + timedelta(hours=2)
        )

    def test_by_organization_meets_gatherings(self):
        qs = AttendingService.by_organization_meets_gatherings(
            meet_slugs=[self.meet.slug],
            user_attended_gathering_ids=[self.gathering.id],
            user_organization_slug=self.organization.slug
        )
        assert qs.count() == 1
        attending_result = qs.first()
        assert attending_result.id == self.attending.id
        assert hasattr(attending_result, 'meet')
        assert hasattr(attending_result, 'character')

    def test_by_family_organization_attendings(self):
        qs = AttendingService.by_family_organization_attendings(
            attendee=self.attendee,
            current_user_organization=self.organization,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.attending.id

    def test_by_assembly_meet_characters(self):
        qs = AttendingService.by_assembly_meet_characters(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug],
            character_slugs=[self.character.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.attending.id

    def test_end_all_activities(self):
        AttendingService.end_all_activities(self.attending)
        
        self.attendingmeet.refresh_from_db()
        self.attendance.refresh_from_db()
        
        # Check if the finish time has been updated to now (roughly)
        assert self.attendingmeet.finish <= datetime.now(timezone.utc)
        assert self.attendance.finish <= datetime.now(timezone.utc)

    def test_destroy_with_associations(self):
        assert Attending.objects.filter(id=self.attending.id).exists()
        assert AttendingMeet.objects.filter(id=self.attendingmeet.id).exists()
        assert Attendance.objects.filter(id=self.attendance.id).exists()
        assert Registration.objects.filter(id=self.registration.id).exists()

        AttendingService.destroy_with_associations(self.attending)

        self.attending.refresh_from_db()
        self.attendingmeet.refresh_from_db()
        self.attendance.refresh_from_db()
        
        assert self.attending.is_removed is True
        assert self.attendingmeet.is_removed is True
        assert self.attendance.is_removed is True
        
        # Because it's the only attending for this registrant's registration, 
        # the registration should also be soft-deleted.
        self.registration.refresh_from_db()
        assert self.registration.is_removed is True
