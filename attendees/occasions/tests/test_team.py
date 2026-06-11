import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from attendees.occasions.models.meet import Meet
from attendees.occasions.models.assembly import Assembly
from attendees.occasions.models.character import Character
from attendees.occasions.models.team import Team
from attendees.whereabouts.models import Division, Organization
from attendees.persons.models import Category
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestTeam:
    def setup_method(self):
        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.division = Division.objects.create(
            display_name="Test Division",
            slug="test-division",
            organization=self.organization,
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(
            display_name="Test Category", type="test", display_order=1
        )
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
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.site_id = str(self.assembly.id)
        self.start = datetime.now(timezone.utc)
        self.finish = self.start + timedelta(hours=2)
        
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.start,
            finish=self.finish,
            display_name="Test Meet",
            slug="test-meet",
            infos={"info": "Test info"},
            site_type=self.site_type,
            site_id=self.site_id,
        )

        self.team = Team.objects.create(
            meet=self.meet,
            slug="test-team",
            display_name="Test Team",
            display_order=1,
            infos={"link": "https://example.com/team"},
            site_type=self.site_type,
            site_id=self.site_id,
        )

    def test_create_team(self):
        assert self.team.pk is not None
        assert self.team.meet == self.meet
        assert self.team.slug == "test-team"
        assert self.team.display_name == "Test Team"
        assert self.team.display_order == 1
        assert self.team.site_type == self.site_type
        assert self.team.site_id == self.site_id
        assert self.team.infos["link"] == "https://example.com/team"

    def test_str(self):
        string_rep = str(self.team)
        assert str(self.meet) in string_rep
        assert "Test Team" in string_rep
