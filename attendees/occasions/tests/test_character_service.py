import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division
from attendees.persons.models import Category, Attendee, Attending, AttendingMeet, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Assembly, Character, Meet, Gathering, Attendance
from attendees.occasions.services.character_service import CharacterService

@pytest.mark.django_db
class TestCharacterService:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Org", slug="test-org")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Div",
            slug="test-div",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Cat")
        self.category_1 = Category.objects.create(id=1, display_name="Scheduled")
        self.family_category = Category.objects.create(id=0, display_name="Family")
        self.relation = Relation.objects.create(id=0, title="test relation", gender=GenderEnum.UNSPECIFIED.value)
        
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character1 = Character.objects.create(
            assembly=self.assembly,
            display_name="Student",
            slug="student",
            type="normal",
            display_order=1
        )
        self.character2 = Character.objects.create(
            assembly=self.assembly,
            display_name="Teacher",
            slug="teacher",
            type="normal",
            display_order=2
        )
        
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.now = datetime.now(timezone.utc)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character1,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=10),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )

        self.gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
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
            character=self.character1,
            finish=self.now + timedelta(days=10)
        )
        
        self.attendance = Attendance.objects.create(
            gathering=self.gathering,
            attending=self.attending,
            character=self.character1,
            start=self.now,
            finish=self.now + timedelta(hours=2)
        )

    def test_by_assembly_meets(self):
        qs = CharacterService.by_assembly_meets(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 2
        # ordered by display_order
        assert qs.first().id == self.character1.id
        assert qs.last().id == self.character2.id

    def test_by_family_meets_gathering_intervals(self):
        qs = CharacterService.by_family_meets_gathering_intervals(user=self.user)
        assert qs.count() == 2
        
    def test_by_organization_assemblies(self):
        # test with all params
        qs = CharacterService.by_organization_assemblies(
            organization=self.organization,
            assemblies=[self.assembly],
            target_attendee=self.attendee,
            search_value="Teach",
            search_operation="contains",
            search_column="display_name"
        )
        assert qs.count() == 1
        assert qs.first().id == self.character2.id
        
        # test without search, ordering puts attended characters first
        qs2 = CharacterService.by_organization_assemblies(
            organization=self.organization,
            assemblies=[self.assembly.id],
            target_attendee=self.attendee,
            search_value=None,
            search_operation=None,
            search_column=None
        )
        assert qs2.count() == 2
        # Since target_attendee has AttendingMeet as character1, it should be first
        assert qs2.first().id == self.character1.id
