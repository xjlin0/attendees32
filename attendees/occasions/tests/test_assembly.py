import pytest
from attendees.occasions.models.assembly import Assembly
from attendees.whereabouts.models import Division, Organization
from attendees.persons.models import Category
from django.contrib.auth.models import Group


@pytest.mark.django_db
class TestAssembly:
    def setup_method(self):
        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.division = Division.objects.create(display_name="Test Division", slug="test-division", organization=self.organization, audience_auth_group=self.group)
        self.category = Category.objects.create(display_name="Test Category", type="test", display_order=1)
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )


    def test_create_assembly(self):
        assert self.assembly.pk is not None
        assert self.assembly.display_name == "Test Assembly"
        assert self.assembly.slug == "test-assembly"
        assert self.assembly.division == self.division
        assert self.assembly.category == self.category
        assert isinstance(self.assembly.infos, dict)


    def test_assembly_str(self):
        assert str(self.assembly) == "Test Assembly"


    def test_get_addresses_empty(self):
        assert self.assembly.get_addresses() == ""
