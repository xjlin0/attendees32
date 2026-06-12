import pytest
from attendees.whereabouts.models.organization import Organization

@pytest.mark.django_db
class TestOrganization:
    def setup_method(self):
        self.organization = Organization.objects.create(
            slug="test-org",
            display_name="Test Organization",
            infos={"hostname": "localhost"},
        )

    def test_create_organization(self):
        assert self.organization.pk is not None
        assert self.organization.slug == "test-org"
        assert self.organization.display_name == "Test Organization"
        assert self.organization.infos["hostname"] == "localhost"

    def test_str(self):
        assert str(self.organization) == "Test Organization"
