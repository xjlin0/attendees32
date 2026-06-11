import pytest
import json
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division, Campus
from attendees.persons.models import Category, Attendee, Attending, AttendingMeet, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Assembly, Character, Meet, Gathering, Attendance
from attendees.occasions.services.gathering_service import GatheringService
from schedule.models import Event, Calendar, EventRelation

@pytest.mark.django_db
class TestGatheringService:
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
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Char",
            slug="test-char",
            type="normal",
        )
        self.campus = Campus.objects.create(organization=self.organization, display_name="Campus A", slug="campus-a")
        self.site_type = ContentType.objects.get_for_model(Campus)
        
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
            site_id=str(self.campus.id),
            infos={"default_time_zone": "America/Los_Angeles"}
        )

        self.gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.campus.id),
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
        qs = GatheringService.by_assembly_meets(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.gathering.id

    def test_by_family_meets(self):
        Attendance.objects.create(
            gathering=self.gathering,
            attending=self.attending,
            character=self.character,
            start=self.now,
            finish=self.now + timedelta(hours=2)
        )
        qs = GatheringService.by_family_meets(
            user=self.user,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.gathering.id

    def test_by_organization_meets(self):
        self.user.groups.add(self.group)
        self.organization.infos["groups_see_all_meets_attendees"] = [self.group.name]
        self.organization.save()
        
        # Test basic retrieval
        qs = GatheringService.by_organization_meets(
            current_user=self.user,
            meet_slugs=[self.meet.slug],
            start=self.now - timedelta(days=1),
            finish=self.now + timedelta(days=1),
            orderbys=[],
            filter=None,
            search_value=None
        )
        assert qs.count() == 1

        # Test search
        qs_search = GatheringService.by_organization_meets(
            current_user=self.user,
            meet_slugs=[self.meet.slug],
            start=None,
            finish=None,
            orderbys=[],
            filter=None,
            search_value="Test Gather",
            search_expression="display_name",
            search_operation="contains"
        )
        assert qs_search.count() == 1

    def test_batch_create(self):
        calendar = Calendar.objects.create(name='test_cal', slug='test_cal')
        event = Event.objects.create(
            start=self.now + timedelta(days=1), 
            end=self.now + timedelta(days=1, hours=2), 
            title='test event', 
            calendar=calendar
        )
        EventRelation.objects.create(
            event=event,
            content_type=ContentType.objects.get_for_model(self.meet),
            object_id=self.meet.id,
            distinction='source'
        )

        begin_str = (self.now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+0000"
        end_str = (self.now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+0000"
        
        result = GatheringService.batch_create(
            begin=begin_str,
            end=end_str,
            meet_slug=self.meet.slug,
            duration=120,
            meet=self.meet,
            user_time_zone='UTC'
        )

        assert result["success"] is True
        assert result["number_created"] == 1

    def test_orderby_parser(self):
        orderbys = [{"selector": "start", "desc": True}, {"selector": "site", "desc": False}]
        parsed = GatheringService.orderby_parser(orderbys)
        assert parsed == ["-start", "site_type", "site_id"]