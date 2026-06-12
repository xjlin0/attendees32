import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from attendees.whereabouts.models import Organization, Division
from attendees.occasions.models import Assembly, Meet, Character, Team, Gathering
from attendees.persons.models import Category
from attendees.occasions.services.team_service import TeamService
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestTeamService:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Organization", slug="test-org")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Character",
            slug="test-character",
            type="normal",
        )
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.now = datetime.now(timezone.utc)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=1),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )
        self.gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )
        self.team1 = Team.objects.create(
            meet=self.meet,
            slug="test-team-1",
            display_name="Test Team One",
            display_order=1,
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )
        self.team2 = Team.objects.create(
            meet=self.meet,
            slug="test-team-2",
            display_name="Test Team Two",
            display_order=2,
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )

    def test_by_assembly_meets(self):
        qs = TeamService.by_assembly_meets(
            assembly_slug=self.assembly.slug,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 2
        assert qs.first().id == self.team1.id
        assert qs.last().id == self.team2.id

    def test_by_organization_meets_basic(self):
        qs = TeamService.by_organization_meets(
            organization_slug=self.organization.slug,
            meet_slugs=[self.meet.slug]
        )
        assert qs.count() == 2

    def test_by_organization_meets_pk(self):
        qs = TeamService.by_organization_meets(
            organization_slug=self.organization.slug,
            meet_slugs=[],
            pk=self.team1.id
        )
        assert qs.count() == 1
        assert qs.first().id == self.team1.id

    def test_by_organization_meets_search(self):
        qs = TeamService.by_organization_meets(
            organization_slug=self.organization.slug,
            meet_slugs=[self.meet.slug],
            search_value="Two",
            search_expression="display_name",
            search_operation="contains"
        )
        assert qs.count() == 1
        assert qs.first().id == self.team2.id

    def test_by_organization_meets_gathering(self):
        qs = TeamService.by_organization_meets(
            organization_slug=self.organization.slug,
            meet_slugs=[],
            gathering=self.gathering.id
        )
        # Should return teams belonging to the meet of this gathering
        assert qs.count() == 2
        
    def test_by_organization_meets_numeric_slugs(self):
        qs = TeamService.by_organization_meets(
            organization_slug=self.organization.slug,
            meet_slugs=[str(self.meet.id)]
        )
        assert qs.count() == 2
