import pytest
from django.db import IntegrityError
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import Utility, Category, Folk, Attendee, FolkAttendee
from attendees.whereabouts.models import Division, Organization
from django.contrib.auth.models import Group
from attendees.persons.models.relation import Relation

@pytest.mark.django_db
class TestFolkAttendee:
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
        self.folk = Folk.objects.create(display_name="Test Folk", division=self.division, category=self.category)
        self.attendee = Attendee.objects.create(
            first_name="John",
            last_name="Doe",
            gender=GenderEnum.UNSPECIFIED.value,
            division=self.division
        )
        self.fa = FolkAttendee.objects.create(
            folk=self.folk,
            attendee=self.attendee,
            role=self.relation,
        )

    def test_create_folk_attendee(self):
        assert self.fa.pk is not None
        assert self.fa.display_order == 1
        assert self.fa.infos == Utility.relationship_infos()


    def test_str_method(self):
        s = str(self.fa)
        assert str(self.folk) in s
        assert str(self.attendee) in s
        assert str(self.relation) in s


    def test_unique_constraint(self):
        with pytest.raises(IntegrityError):
            FolkAttendee.objects.create(
                folk=self.folk,
                attendee=self.attendee,
                role=self.relation,
            )
