import pytest
from attendees.users.models import User
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Registration, Attendee, Category, Relation
from attendees.whereabouts.models import Division, Organization
from attendees.occasions.models import Assembly
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestRegistration:
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

        self.user = User.objects.create_user(username='testuser', password='12345')
        self.assembly = Assembly.objects.create(display_name="Test Assembly", slug='test-assembly', division=self.division, category=self.category)
        self.attendee = Attendee.objects.create(user=self.user, first_name="John", last_name="Doe", gender=GenderEnum.UNSPECIFIED.value, division=self.division)

    def test_create_registration(self):
        registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee,
            infos={"price": "150.75", "donation": "85.00"}
        )
        assert registration.id is not None
        assert registration.assembly == self.assembly
        assert registration.registrant == self.attendee
        assert registration.infos == {"price": "150.75", "donation": "85.00"}

    def test_registration_str(self):
        registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee
        )
        assert str(registration) == f"{self.attendee} {self.assembly}"

    def test_registration_default_values(self):
        registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee
        )
        assert registration.infos == {}

    def test_update_registration(self):
        registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee,
            infos={"price": "150.75", "donation": "85.00"}
        )
        registration.infos["credit"] = "35.50"
        registration.save()

        updated_registration = Registration.objects.get(id=registration.id)
        assert updated_registration.infos == {"price": "150.75", "donation": "85.00", "credit": "35.50"}

    def test_delete_registration(self):
        registration = Registration.objects.create(
            assembly=self.assembly,
            registrant=self.attendee
        )
        registration_id = registration.id
        registration.delete()

        with pytest.raises(Registration.DoesNotExist):
            Registration.objects.get(id=registration_id)
