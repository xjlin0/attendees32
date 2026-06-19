import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from address.models import Address, Locality, State, Country
from attendees.whereabouts.services.geocoding_service import GeocodingService

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
class TestGeocodingService:

    @patch('attendees.whereabouts.services.geocoding_service.requests.get')
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
            result = GeocodingService.geocode_address(target_id)

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
            result = GeocodingService.geocode_address(address_setup['address1'].id)
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
            with patch('attendees.whereabouts.services.geocoding_service.requests.get') as mock_get:
                result = GeocodingService.geocode_address(add1.id)
                assert result is True
                mock_get.assert_not_called()
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    @patch('attendees.whereabouts.services.geocoding_service.requests.get')
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
            result = GeocodingService.geocode_address(address_setup['address1'].id)
            assert result is False
            
            # Verify database wasn't touched
            add1 = Address.objects.get(id=address_setup['address1'].id)
            assert add1.latitude is None
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key
