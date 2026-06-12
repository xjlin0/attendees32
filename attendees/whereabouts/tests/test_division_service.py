import pytest
from django.contrib.auth.models import Group
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.division import Division
from attendees.whereabouts.services.division_service import DivisionService

@pytest.mark.django_db
class TestDivisionService:
    def setup_method(self):
        self.org1 = Organization.objects.create(display_name="Org 1", slug="org-1")
        self.org2 = Organization.objects.create(display_name="Org 2", slug="org-2")
        self.group = Group.objects.create(name="Test Group")
        
        self.div_b = Division.objects.create(
            organization=self.org1,
            display_name="Division B",
            slug="div-b",
            audience_auth_group=self.group
        )
        self.div_a = Division.objects.create(
            organization=self.org1,
            display_name="Division A",
            slug="div-a",
            audience_auth_group=self.group
        )
        self.div_other = Division.objects.create(
            organization=self.org2,
            display_name="Division Other",
            slug="div-other",
            audience_auth_group=self.group
        )

    def test_by_organization(self):
        # Fetching for org-1 should return div_a and div_b, ordered by display_name
        qs = DivisionService.by_organization("org-1")
        assert qs.count() == 2
        
        # Check ordering
        results = list(qs)
        assert results[0] == self.div_a
        assert results[1] == self.div_b

    def test_by_organization_empty(self):
        # Fetching for an non-existent organization should return empty
        qs = DivisionService.by_organization("non-existent-org")
        assert qs.count() == 0
