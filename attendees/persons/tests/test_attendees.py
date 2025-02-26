import pytest
from datetime import date
from django.core.exceptions import ValidationError
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Attendee, Category, Relation
from attendees.whereabouts.models import Division, Organization
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestAttendee:
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

    def test_create_attendee(self):
        attendee = Attendee(
            first_name="John",
            last_name="Doe",
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        attendee.save()
        assert attendee.id is not None

    def test_create_attendee_without_name(self):
        attendee = Attendee(
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        with pytest.raises(ValidationError):
            attendee.clean()

    def test_attendee_age(self):
        actual_birthday = date(2000, 1, 1)
        attendee = Attendee(
            first_name="Jane",
            last_name="Smith",
            actual_birthday=actual_birthday,
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        attendee.save()
        expected_age = (date.today() - actual_birthday).days // 365
        assert attendee.age() == expected_age

    def test_attendee_str(self):
        attendee = Attendee(
            first_name="Alice",
            last_name="Johnson",
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        attendee.save()
        assert str(attendee) == "Alice Johnson"

    def test_attendee_division_label(self):
        attendee = Attendee(
            first_name="Division",
            last_name="Tester",
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        attendee.save()
        assert attendee.division_label == "Test Division"
