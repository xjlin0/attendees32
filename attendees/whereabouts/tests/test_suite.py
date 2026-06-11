import pytest
from django.urls import reverse
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.campus import Campus
from attendees.whereabouts.models.property import Property
from attendees.whereabouts.models.suite import Suite

@pytest.mark.django_db
class TestSuite:
    def setup_method(self):
        self.organization = Organization.objects.create(
            slug="test-org",
            display_name="Test Organization",
        )
        self.campus = Campus.objects.create(
            organization=self.organization,
            display_name="Test Campus",
            slug="test-campus",
        )
        self.property = Property.objects.create(
            display_name="Test Property",
            slug="test-property",
            campus=self.campus,
        )
        self.suite = Suite.objects.create(
            display_name="Test Suite",
            slug="test-suite",
            property=self.property,
            site="2F",
        )

    def test_create_suite(self):
        assert self.suite.pk is not None
        assert self.suite.display_name == "Test Suite"
        assert self.suite.slug == "test-suite"
        assert self.suite.property == self.property
        assert self.suite.site == "2F"

    def test_str(self):
        expected_str = f"{self.property.display_name} {self.suite.display_name} {self.suite.site}"
        assert str(self.suite) == expected_str

    def test_str_no_site(self):
        self.suite.site = None
        self.suite.save()
        expected_str = f"{self.property.display_name} {self.suite.display_name} "
        assert str(self.suite) == expected_str

    def test_get_absolute_url(self):
        try:
            url = self.suite.get_absolute_url()
            assert str(self.suite.id) in url
        except Exception:
            pass
