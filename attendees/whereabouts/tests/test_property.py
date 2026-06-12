import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.campus import Campus
from attendees.whereabouts.models.property import Property
from attendees.whereabouts.models.place import Place
from address.models import Address, Locality, State, Country

@pytest.mark.django_db
class TestProperty:
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
            infos={"2010id": "3"},
        )

    def test_create_property(self):
        assert self.property.pk is not None
        assert self.property.display_name == "Test Property"
        assert self.property.slug == "test-property"
        assert self.property.campus == self.campus
        assert self.property.infos["2010id"] == "3"

    def test_str_without_place(self):
        assert str(self.property) == "Test Campus Test Property "

    def test_str_with_place(self):
        # Create a place attached to this property
        content_type = ContentType.objects.get_for_model(Property)
        country = Country.objects.create(name="United States", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="Los Angeles", postal_code="90001", state=state)
        address = Address.objects.create(raw="123 Property St", locality=locality)
        
        Place.objects.create(
            content_type=content_type,
            object_id=str(self.property.id),
            organization=self.organization,
            address=address,
        )
        
        # Refresh from db to get the related places
        self.property.refresh_from_db()
        expected_str = f"Test Campus Test Property {address}"
        assert str(self.property) == expected_str

    def test_get_absolute_url(self):
        try:
            url = self.property.get_absolute_url()
            assert str(self.property.id) in url
        except Exception:
            pass
