import pytest
from uuid import uuid4
from attendees.persons.models import Folk, Category, Utility
from attendees.whereabouts.models import Division, Organization
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestFolk:
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

    def test_create_folk(self):
        folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category,
            display_name="Family Group",
            display_order=1,
            infos={"print_directory": True}
        )
        assert folk.id is not None
        assert folk.division == self.division
        assert folk.category == self.category
        assert folk.display_name == "Family Group"
        assert folk.display_order == 1
        assert folk.infos == {"print_directory": True}

    def test_folk_str(self):
        folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category,
            display_name="Friends Group"
        )
        assert str(folk) == f"{self.division} {self.category} Friends Group"

    def test_folk_default_values(self):
        folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category
        )
        assert folk.display_order == 0
        assert folk.infos == Utility.folk_infos()

    def test_update_folk(self):
        folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category,
            display_name="Old Group"
        )
        folk.display_name = "Updated Group"
        folk.save()

        updated_folk = Folk.objects.get(id=folk.id)
        assert updated_folk.display_name == "Updated Group"

    def test_delete_folk(self):
        folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category,
            display_name="Temporary Group"
        )
        folk_id = folk.id
        folk.delete()

        with pytest.raises(Folk.DoesNotExist):
            Folk.objects.get(id=folk_id)
