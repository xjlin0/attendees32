import pytest
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.division import Division
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestDivision:
    def setup_method(self):
        self.organization = Organization.objects.create(
            slug="test-org",
            display_name="Test Organization",
        )
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group,
            infos={"show_attendee_infos": {"insurer": True}},
        )

    def test_create_division(self):
        assert self.division.pk is not None
        assert self.division.organization == self.organization
        assert self.division.display_name == "Test Division"
        assert self.division.slug == "test-division"
        assert self.division.audience_auth_group == self.group
        assert self.division.infos["show_attendee_infos"]["insurer"] is True

    def test_str(self):
        assert str(self.division) == "Test Division"
