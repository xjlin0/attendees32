import pytest
from attendees.occasions.models.character import Character
from attendees.occasions.models.assembly import Assembly
from attendees.whereabouts.models import Division, Organization
from attendees.persons.models import Category
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestCharacter:
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
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Character",
            display_order=1,
            slug="test-assembly-test-character",
            type="normal",
        )

    def test_create_character(self):
        assert self.character.pk is not None
        assert self.character.assembly == self.assembly
        assert self.character.display_name == "Test Character"
        assert self.character.slug == "test-assembly-test-character"
        assert self.character.type == "normal"
        assert isinstance(self.character.infos, dict)

    def test_character_str(self):
        s = str(self.character)
        assert self.assembly.display_name in s
        assert "Test Character" in s
        assert "normal" in s
