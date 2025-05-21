import pytest
from datetime import datetime, timedelta, timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Category, Relation, Attendee, Registration, Attending, AttendingMeet
from attendees.whereabouts.models import Organization, Division
from attendees.occasions.models import Price, Gathering, Character, Team, Meet, Assembly, Attendance
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestAttendance:

    @pytest.fixture
    def setup_objects(self):
        relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
        organization = Organization.objects.create(display_name="Test Org")
        group = Group.objects.create(name="Test Group")
        division = Division.objects.create(organization=organization, display_name="Test Division", slug="test-division", audience_auth_group=group)
        category = Category.objects.create(id=25, display_name="Test Category", type="test", display_order=1)
        assembly = Assembly.objects.create(display_name="Test Assembly", slug="test-assembly", division=division, category=category)
        meet = Meet.objects.create(display_name="Test Meet", assembly=assembly, finish=datetime.now(timezone.utc) + timedelta(days=1), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        gathering = Gathering.objects.create(display_name="Test Gathering", meet=meet, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc) + timedelta(hours=2), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        character = Character.objects.create(display_name="Test Character", assembly=assembly)
        attendee = Attendee.objects.create(first_name="John", last_name="Doe", gender=0, division=division)
        registration = Registration.objects.create(registrant=attendee, assembly=assembly)
        price = Price.objects.create(price_value=100.0, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc)+timedelta(days=9))
        attending = Attending.objects.create(registration=registration, attendee=attendee)
        team = Team.objects.create(display_name="Test Team", slug="test-team", meet=meet, site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        # Add meet to attending.meets
        attending_meet = AttendingMeet.objects.create(
            attending=attending,
            meet=meet,
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(hours=1),
            character=character,
            category=category,
            team=team,
        )
        # attending.meets.add(meet)
        # Patch attendee display_label and main_contact for attendance_label property
        # attendee.display_label = "John Doe"
        # attendee.save()
        # attending.main_contact = attendee
        # attending.save()
        return {
            "organization": organization,
            "division": division,
            "category": category,
            "assembly": assembly,
            "meet": meet,
            "gathering": gathering,
            "character": character,
            "attendee": attendee,
            "registration": registration,
            "attending": attending,
            "attending_meet": attending_meet,
            "team": team,
        }

    def test_create_attendance(self, setup_objects):
        attendance = Attendance.objects.create(
            gathering=setup_objects["gathering"],
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert attendance.pk is not None
        assert attendance.display_order == 0
        assert isinstance(attendance.infos, dict)

    def test_str_method(self, setup_objects):
        attendance = Attendance.objects.create(
            gathering=setup_objects["gathering"],
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        s = str(attendance)
        assert "Test Gathering" in s
        assert "Test Character" in s

    def test_attendance_info_property(self, setup_objects):
        attendance = Attendance.objects.create(
            gathering=setup_objects["gathering"],
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        info = attendance.attendance_info
        assert setup_objects["meet"].display_name in info
        assert setup_objects["gathering"].start.strftime("%b.%d'%y") in info

    def test_attendance_label_property(self, setup_objects):
        attendance = Attendance.objects.create(
            gathering=setup_objects["gathering"],
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        label = attendance.attendance_label
        assert "John Doe" in label

    def test_clean_valid(self, setup_objects):
        attendance = Attendance(
            gathering=setup_objects["gathering"],
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        # Should not raise
        attendance.clean()

    def test_clean_invalid_assembly(self, setup_objects):
        # Create a character with a different assembly
        other_assembly = Assembly.objects.create(display_name="Other Assembly", slug="other-assembly", division=setup_objects["division"], category=setup_objects["category"])
        other_character = Character.objects.create(display_name="Other Character", assembly=other_assembly, slug="other-assembly-other-character")
        attendance = Attendance(
            gathering=setup_objects["gathering"],
            character=other_character,
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        with pytest.raises(ValidationError):
            attendance.clean()

    def test_clean_invalid_meet(self, setup_objects):
        # Create a gathering with a meet not in attending.meets
        other_assembly = Assembly.objects.create(display_name="Other Assembly2", slug="other-assembly2", division=setup_objects["division"], category=setup_objects["category"])
        other_meet = Meet.objects.create(display_name="Other Meet", slug="other-meet", assembly=other_assembly, finish=datetime.now(timezone.utc) + timedelta(days=1), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        other_gathering = Gathering.objects.create(display_name="Other Gathering", meet=other_meet, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc) + timedelta(hours=2), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        attendance = Attendance(
            gathering=other_gathering,
            character=setup_objects["character"],
            attending=setup_objects["attending"],
            category=setup_objects["category"],
            team=setup_objects["team"],
            start=datetime.now(timezone.utc),
        )
        with pytest.raises(ValidationError):
            attendance.clean()