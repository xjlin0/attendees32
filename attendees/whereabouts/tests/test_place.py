import pytest
from uuid import UUID
from datetime import date
from django.contrib.contenttypes.models import ContentType
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.place import Place
from address.models import Address, Locality, State, Country

@pytest.mark.django_db
class TestPlace:
    def setup_method(self):
        self.organization = Organization.objects.create(
            slug="test-org",
            display_name="Test Organization",
        )
        self.content_type = ContentType.objects.get_for_model(Organization)
        
        self.country = Country.objects.create(name="United States", code="US")
        self.state = State.objects.create(name="California", code="CA", country=self.country)
        self.locality = Locality.objects.create(name="Los Angeles", postal_code="90001", state=self.state)
        self.address = Address.objects.create(raw="123 Main St", locality=self.locality)

        self.place = Place.objects.create(
            content_type=self.content_type,
            object_id=str(self.organization.id),
            organization=self.organization,
            address=self.address,
            display_name="Main Office",
            display_order=1,
            start=date(2020, 1, 1),
        )

    def test_create_place(self):
        assert self.place.pk is not None
        assert isinstance(self.place.pk, UUID)
        assert self.place.organization == self.organization
        assert self.place.subject == self.organization
        assert self.place.address == self.address
        assert self.place.display_name == "Main Office"
        assert self.place.display_order == 1
        assert self.place.start == date(2020, 1, 1)

    def test_str(self):
        assert str(self.place) == f"{self.address} {self.organization}"

    def test_street_property(self):
        assert self.place.street == str(self.address)
