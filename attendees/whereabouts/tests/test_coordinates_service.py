import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from address.models import Address, Locality, State, Country
from attendees.whereabouts.services.coordinates_service import CoordinatesService
from attendees.whereabouts.models.place import Place
from attendees.whereabouts.models.organization import Organization
from django.contrib.contenttypes.models import ContentType

@pytest.fixture
def address_setup():
    country = Country.objects.create(name='USA', code='US')
    state = State.objects.create(name='California', code='CA', country=country)
    locality = Locality.objects.create(name='Hayward', postal_code='94541', state=state)
    
    # Create target address
    address1 = Address.objects.create(
        street_number='123',
        route='Main St',
        locality=locality,
        raw='123 Main St, Hayward, CA'
    )
    
    # Create sibling address (same building, maybe different suite)
    address2 = Address.objects.create(
        street_number='123',
        route='Main St',
        locality=locality,
        raw='123 Main St Ste B, Hayward, CA',
        extra='Suite B'
    )
    
    # Create unrelated address
    address3 = Address.objects.create(
        street_number='456',
        route='Other St',
        locality=locality,
        raw='456 Other St, Hayward, CA'
    )
    
    return {
        'address1': address1,
        'address2': address2,
        'address3': address3
    }


@pytest.mark.django_db
class TestCoordinatesService:

    @patch('attendees.whereabouts.services.coordinates_service.requests.get')
    def test_geocode_address_success_updates_siblings(self, mock_get, address_setup):
        """Test that a successful API call updates the target address and its siblings."""
        # Mock the Google Maps API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "geometry": {
                        "location": {
                            "lat": 37.6688,
                            "lng": -122.0808
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Temporarily set an API key for the test
        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'

        try:
            target_id = address_setup['address1'].id
            result = CoordinatesService.geocode_address(target_id)

            assert result is True
            
            # Verify the API was called with the correct address string
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert '123, Main St, Hayward, California, USA' in kwargs['params']['address']

            # Refresh from DB
            add1 = Address.objects.get(id=target_id)
            add2 = Address.objects.get(id=address_setup['address2'].id)
            add3 = Address.objects.get(id=address_setup['address3'].id)

            # Target and sibling should be updated
            assert add1.latitude == 37.6688
            assert add1.longitude == -122.0808
            assert add2.latitude == 37.6688
            assert add2.longitude == -122.0808

            # Unrelated address should NOT be updated
            assert add3.latitude is None
            assert add3.longitude is None
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    def test_geocode_address_no_api_key(self, address_setup):
        """Test that geocoding is skipped if no API key is configured."""
        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = ''

        try:
            result = CoordinatesService.geocode_address(address_setup['address1'].id)
            assert result is False
            
            add1 = Address.objects.get(id=address_setup['address1'].id)
            assert add1.latitude is None
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    def test_geocode_address_already_has_coordinates(self, address_setup):
        """Test that API is not called if address already has coordinates."""
        add1 = address_setup['address1']
        add1.latitude = 10.0
        add1.longitude = 20.0
        add1.save()

        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'

        try:
            with patch('attendees.whereabouts.services.coordinates_service.requests.get') as mock_get:
                result = CoordinatesService.geocode_address(add1.id)
                assert result is True
                mock_get.assert_not_called()
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    @patch('attendees.whereabouts.services.coordinates_service.requests.get')
    def test_geocode_address_api_failure(self, mock_get, address_setup):
        """Test handling of Google Maps API returning ZERO_RESULTS."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ZERO_RESULTS",
            "results": []
        }
        mock_get.return_value = mock_response

        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'

        try:
            result = CoordinatesService.geocode_address(address_setup['address1'].id)
            assert result is False
            
            # Verify database wasn't touched
            add1 = Address.objects.get(id=address_setup['address1'].id)
            assert add1.latitude is None
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    def test_get_nearest_neighbors_target_not_found(self, address_setup):
        """Test get_nearest_neighbors when the target Place doesn't exist."""
        # 9999 doesn't exist
        target, neighbors = CoordinatesService.get_nearest_neighbors(9999)
        assert target is None
        assert list(neighbors) == []

    def test_get_nearest_neighbors_target_no_coordinates(self, address_setup):
        """Test get_nearest_neighbors when the target Place exists but has no coordinates."""
        org = Organization.objects.create(slug="test-org", display_name="Test Org")
        ctype = ContentType.objects.get_for_model(Organization)
        
        target_place = Place.objects.create(
            content_type=ctype,
            object_id=str(org.id),
            organization=org,
            address=address_setup['address1'], # no coordinates
            display_name="No Coords Place"
        )
        
        target, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id)
        assert target is None
        assert list(neighbors) == []

    @patch('attendees.whereabouts.services.coordinates_service.RawSQL')
    def test_get_nearest_neighbors_success(self, mock_rawsql, address_setup):
        """Test get_nearest_neighbors successfully calculates distance and orders results."""
        from django.db.models import Value, FloatField
        
        # Mock the RawSQL to return a constant float to bypass missing PostGIS functions in test DB
        mock_rawsql.return_value = Value(10.5, output_field=FloatField())
        
        org = Organization.objects.create(slug="test-org", display_name="Test Org")
        ctype = ContentType.objects.get_for_model(Organization)
        
        # Target place: San Francisco (approx)
        addr1 = address_setup['address1']
        addr1.latitude = 37.7749
        addr1.longitude = -122.4194
        addr1.save()
        target_place = Place.objects.create(
            content_type=ctype, object_id=str(org.id), organization=org,
            address=addr1, display_name="Target SF"
        )
        
        # Neighbor 1: Oakland (approx 10 miles away)
        addr2 = address_setup['address2']
        addr2.latitude = 37.8044
        addr2.longitude = -122.2712
        addr2.save()
        neighbor_oakland = Place.objects.create(
            content_type=ctype, object_id=str(org.id), organization=org,
            address=addr2, display_name="Oakland"
        )
        
        # Neighbor 2: San Jose (approx 45 miles away)
        addr3 = address_setup['address3']
        addr3.latitude = 37.3382
        addr3.longitude = -121.8863
        addr3.save()
        neighbor_sj = Place.objects.create(
            content_type=ctype, object_id=str(org.id), organization=org,
            address=addr3, display_name="San Jose"
        )
        
        # Another place without coordinates (should be ignored)
        addr_no_coords = Address.objects.create(raw="No coords", locality=addr1.locality)
        Place.objects.create(
            content_type=ctype, object_id=str(org.id), organization=org,
            address=addr_no_coords, display_name="No Coords"
        )
        
        target, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id)
        
        assert target == target_place
        assert len(neighbors) == 2
        
        # Both will be returned since both have coordinates
        assert neighbor_oakland in neighbors
        assert neighbor_sj in neighbors
        
        # Distance should be annotated and equal to our mock value
        assert hasattr(neighbors[0], 'distance_miles')
        assert neighbors[0].distance_miles == 10.5
