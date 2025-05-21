import pytest
from datetime import datetime, timedelta, timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Attending, Attendee, Registration, Relation, Category, AttendingMeet
from attendees.whereabouts.models import Division, Organization
from attendees.occasions.models import Price, Gathering, Meet, Assembly, Character, Team
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestAttendingMeet:

    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(organization=self.organization, display_name="Test Division", slug="test-division", audience_auth_group=self.group)
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
        self.assembly = Assembly.objects.create(display_name="Test Assembly", slug='test-assembly', division=self.division, category=self.category)
        self.assembly2 = Assembly.objects.create(display_name="Different Assembly", slug='different-assembly', division=self.division, category=self.category)
        self.character = Character.objects.create(display_name="Character", assembly=self.assembly)
        self.attendee = Attendee.objects.create(first_name="John", last_name="Doe", gender=GenderEnum.UNSPECIFIED.value, division=self.division)
        self.registration = Registration.objects.create(registrant=self.attendee, assembly=self.assembly)
        self.price = Price.objects.create(price_value=100.0, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc) + timedelta(days=9))
        self.meet = Meet.objects.create(display_name="Test Meet", assembly=self.assembly, finish=datetime.now(timezone.utc) + timedelta(days=8), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        self.gathering = Gathering.objects.create(display_name="Test Gathering", meet=self.meet, start=datetime.now(timezone.utc), finish=datetime.now(timezone.utc) + timedelta(days=1), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        self.team = Team.objects.create(display_name="Test Team", slug="test-team", meet=self.meet, site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        self.team2 = Team.objects.create(display_name="Test Team2", slug="test-team2", meet=self.meet, site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        self.attending = Attending.objects.create(registration=self.registration, price=self.price, attendee=self.attendee)

    def test_create_attending_meet(self):
        attending_meet = AttendingMeet.objects.create(
            attending=self.attending,
            meet=self.meet,
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(hours=1),
            character=self.character,
            category=self.category,
            team=self.team,
        )
        assert attending_meet.attending == self.attending
        assert attending_meet.meet == self.meet
        assert attending_meet.character == self.character
        assert attending_meet.category == self.category
        assert attending_meet.team == self.team

    def test_attending_meet_clean(self):
        different_assembly_character = Character.objects.create(display_name="Different Assembly Character", assembly=self.assembly2, slug='different-assembly-character')
        attending_meet = AttendingMeet(
            attending=self.attending,
            meet=self.meet,
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(hours=1),
            character=different_assembly_character,
            category=self.category,
            team=self.team,
        )
        with pytest.raises(ValidationError):
            attending_meet.clean()

    def test_check_participation_of(self):
        attending_meet = AttendingMeet.objects.create(
            attending=self.attending,
            meet=self.meet,
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(hours=1),
            character=self.character,
            category=self.category,
            team=self.team,
        )
        assert AttendingMeet.check_participation_of(self.attendee, self.meet) is True
        attending_meet.finish = datetime.now(timezone.utc) - timedelta(hours=1)
        attending_meet.save()
        assert AttendingMeet.check_participation_of(self.attendee, self.meet) is False
        attending_meet.finish = datetime.now(timezone.utc) + timedelta(hours=1)
        attending_meet.save()
