import pytest
from datetime import datetime, timedelta
from django.contrib.contenttypes.models import ContentType
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Attending, Attendee, Registration, Relation, Category, AttendingMeet
from attendees.whereabouts.models import Division, Organization
from attendees.occasions.models import Price, Gathering, Meet, Assembly, Character
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestAttending:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
        self.assembly = Assembly.objects.create(display_name="Test Assembly", slug='test-assembly', division=self.division, category=self.category)
        self.character = Character.objects.create(display_name="Character", assembly=self.assembly)
        self.attendee = Attendee.objects.create(first_name="John", last_name="Doe", gender=GenderEnum.UNSPECIFIED.value, division=self.division)
        self.registration = Registration.objects.create(
            registrant=self.attendee,
            assembly=self.assembly
        )
        self.price = Price.objects.create(price_value=100.0, start=datetime.now(), finish=datetime.now()+timedelta(days=9))
        self.meet = Meet.objects.create(display_name="Test Meet", assembly=self.assembly, finish=datetime.now()+timedelta(days=8), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)
        self.gathering = Gathering.objects.create(display_name="Test Gathering", meet=self.meet, start=datetime.now(), finish=datetime.now()+timedelta(days=1), site_type=ContentType.objects.first(), site_id=ContentType.objects.first().model_class().objects.first().id)

    def test_create_attending(self):
        attending = Attending.objects.create(
            registration=self.registration,
            price=self.price,
            attendee=self.attendee,
            category="normal",
            infos={"grade": 5, "age": 11, "bed_needs": 1, "mobility": 300}
        )
        assert attending.id is not None
        assert attending.registration == self.registration
        assert attending.price == self.price
        assert attending.attendee == self.attendee
        assert attending.category == "normal"
        assert attending.infos == {"grade": 5, "age": 11, "bed_needs": 1, "mobility": 300}

    def test_attending_str(self):
        attending = Attending.objects.create(
            registration=self.registration,
            price=self.price,
            attendee=self.attendee,
            category="normal"
        )
        AttendingMeet.objects.create(
            category=self.category,
            attending=attending,
            meet=self.meet,
            character=self.character,
            start=self.meet.start,
            finish=self.meet.finish
        )
        assert str(attending) == f"{self.attendee} {self.meet.display_name}"

    def test_attending_default_values(self):
        attending = Attending.objects.create(
            registration=self.registration,
            price=self.price,
            attendee=self.attendee,
            category="normal"
        )
        assert attending.infos == {}
        assert attending.category == "normal"

    def test_update_attending(self):
        attending = Attending.objects.create(
            registration=self.registration,
            price=self.price,
            attendee=self.attendee,
            category="normal",
            infos={"grade": 5, "age": 11}
        )
        attending.infos["bed_needs"] = 1
        attending.save()

        updated_attending = Attending.objects.get(id=attending.id)
        assert updated_attending.infos == {"grade": 5, "age": 11, "bed_needs": 1}

    def test_delete_attending(self):
        attending = Attending.objects.create(
            registration=self.registration,
            price=self.price,
            attendee=self.attendee,
            category="normal"
        )
        attending_id = attending.id
        attending.delete()

        with pytest.raises(Attending.DoesNotExist):
            Attending.objects.get(id=attending_id)
