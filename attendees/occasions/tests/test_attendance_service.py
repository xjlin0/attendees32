import pytest
import json
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division, Room
from attendees.persons.models import Category, Attendee, Attending, AttendingMeet, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Assembly, Character, Meet, Gathering, Attendance, Team
from attendees.occasions.services.attendance_service import AttendanceService

@pytest.mark.django_db
class TestAttendanceService:
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
            infos={"default_time_zone": "America/Los_Angeles"}
        )

        self.gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.room.id),
            infos={"generate_attendance": True}
        )
        
        self.team = Team.objects.create(
            meet=self.meet,
            slug="test-team",
            display_name="Test Team",
            display_order=1,
            site_type=self.site_type,
            site_id=str(self.room.id),
        )

        self.user = User.objects.create(
            username="testuser",
            email="testuser@example.com",
            organization=self.organization
        )
        self.user.groups.add(self.group)
        self.organization.infos["groups_see_all_meets_attendees"] = [self.group.name]
        self.organization.save()

        self.attendee = Attendee.objects.create(
            first_name="John",
            last_name="Doe",
            division=self.division,
            user=self.user,
            gender="unspecified",
            infos={"names": {"original": "John Doe Org"}}
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
            team=self.team,
            finish=self.now + timedelta(days=10)
        )

        self.attendance = Attendance.objects.create(
            gathering=self.gathering,
            attending=self.attending,
            character=self.character,
            team=self.team,
            category=self.category,
            start=self.now,
            finish=self.now + timedelta(hours=2)
        )

    def test_by_assembly_meets_characters_gathering_intervals(self):
        qs = AttendanceService.by_assembly_meets_characters_gathering_intervals(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug],
            gathering_start=self.now - timedelta(days=1),
            gathering_finish=self.now + timedelta(days=1),
            character_slugs=[self.character.slug]
        )
        assert qs.count() == 1
        assert qs.first().id == self.attendance.id

    def test_by_organization_meets_gatherings_intervals(self):
        qs = AttendanceService.by_organization_meets_gatherings_intervals(
            organization_slug=self.organization.slug,
            meet_slugs=[self.meet.slug],
            gathering_ids=[self.gathering.id],
            gathering_start=self.now - timedelta(days=1),
            gathering_finish=self.now + timedelta(days=1)
        )
        assert qs.count() == 1
        assert qs.first().id == self.attendance.id

    def test_by_family_meets_gathering_intervals(self):
        qs = AttendanceService.by_family_meets_gathering_intervals(
            admin_checking=False,
            attendee=self.attendee,
            current_user_organization=self.organization,
            meet_slugs=[self.meet.slug],
            gathering_start=self.now - timedelta(days=1),
            gathering_finish=self.now + timedelta(days=1)
        )
        assert qs.count() == 1
        assert qs.first().id == self.attendance.id

    def test_by_organization_meet_characters(self):
        qs = AttendanceService.by_organization_meet_characters(
            current_user=self.user,
            meet_slugs=[self.meet.slug],
            character_slugs=[self.character.slug],
            start=self.now - timedelta(days=1),
            finish=self.now + timedelta(days=1),
            gatherings=[],
            orderbys=[],
            attendee=None,
            photo_instead_of_gathering_assembly=False,
            search_value=None,
            search_expression=None,
            search_operation=None,
            filter=None
        )
        assert qs.count() == 1
        first_item = qs.first()
        assert first_item.id == self.attendance.id
        
        # Test annotation
        assert hasattr(first_item, 'attending_name')
        assert "John Doe" in first_item.attending_name

    def test_attendance_count(self):
        qs = AttendanceService.attendance_count(
            user_organization=self.organization,
            meet_slugs=[self.meet.slug],
            character_slugs=[self.character.slug],
            team_ids=[self.team.id],
            category_ids=[self.category.id],
            start=self.now - timedelta(days=1),
            finish=self.now + timedelta(days=1),
            orderbys=[],
            name_search=[[None]]
        )
        assert qs.count() == 1
        first_item = qs.first()
        assert first_item['count'] == 1
        assert "Test Char" in first_item['characters']
        assert "Test Team" in first_item['teams']

    def test_batch_create(self):
        # We delete existing attendance to let batch_create make one
        self.attendance.delete()
        
        begin_str = (self.now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+0000"
        end_str = (self.now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f") + "+0000"
        
        result = AttendanceService.batch_create(
            begin=begin_str,
            end=end_str,
            meet_slug=self.meet.slug,
            meet=self.meet,
            user_time_zone='UTC',
            attendee_id=self.attendee.id
        )

        assert result["success"] is True
        assert result["attendance_created"] == 1
        assert Attendance.objects.filter(gathering=self.gathering, attending=self.attending).exists()

    def test_orderby_parser(self):
        orderbys = [{"selector": "character", "desc": True}, {"selector": "start", "desc": False}]
        parsed = list(AttendanceService.orderby_parser(orderbys))
        assert parsed == ["-character__display_name", "start"]