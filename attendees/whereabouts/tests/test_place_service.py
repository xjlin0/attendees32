import pytest
from address.models import Address, Locality, State, Country
from attendees.whereabouts.models import Organization, Place
from attendees.whereabouts.services import PlaceService
from django.contrib.contenttypes.models import ContentType

@pytest.mark.django_db
class TestPlaceService:
    def setup_method(self):
        self.org = Organization.objects.create(slug="test-org", display_name="Test Organization")
        self.ct = ContentType.objects.get_for_model(Organization)
        
        country = Country.objects.create(name="USA", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        self.locality = Locality.objects.create(name="Los Angeles", postal_code="90001", state=state)
        
        self.address1 = Address.objects.create(raw="123 Single Use St", locality=self.locality)
        self.address2 = Address.objects.create(raw="456 Shared St", locality=self.locality)
        
        self.place_unique = Place.objects.create(
            content_type=self.ct, object_id=str(self.org.id), organization=self.org,
            address=self.address1, display_name="Unique Place"
        )
        
        self.place_shared1 = Place.objects.create(
            content_type=self.ct, object_id=str(self.org.id), organization=self.org,
            address=self.address2, display_name="Shared Place 1"
        )
        self.place_shared2 = Place.objects.create(
            content_type=self.ct, object_id="different_id", organization=self.org,
            address=self.address2, display_name="Shared Place 2"
        )

    def test_destroy_with_associations_unique_address(self):
        """Test that destroying a place with a unique address also deletes the address."""
        assert Address.objects.filter(id=self.address1.id).exists()
        
        PlaceService.destroy_with_associations(self.place_unique)
        
        assert not Place.objects.filter(id=self.place_unique.id).exists()
        assert not Address.objects.filter(id=self.address1.id).exists()

    def test_destroy_with_associations_shared_address(self):
        """Test that destroying a place with a shared address keeps the address for other places."""
        assert Address.objects.filter(id=self.address2.id).exists()
        
        PlaceService.destroy_with_associations(self.place_shared1)
        
        assert not Place.objects.filter(id=self.place_shared1.id).exists()
        # The address should NOT be deleted because place_shared2 still uses it
        assert Address.objects.filter(id=self.address2.id).exists()
        assert Place.objects.filter(id=self.place_shared2.id).exists()
