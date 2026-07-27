import pytest
from io import StringIO
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from address.models import Address, Locality, State, Country
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.place import Place

@pytest.fixture
def address_setup():
    country = Country.objects.create(name='USA', code='US')
    state = State.objects.create(name='California', code='CA', country=country)
    locality = Locality.objects.create(name='Hayward', postal_code='94541', state=state)

    org = Organization.objects.create(
        slug="test-org",
        display_name="Test Organization",
    )
    ct = ContentType.objects.get_for_model(Organization)

    # 1. Address with coordinates
    addr_with_coords = Address.objects.create(
        street_number='123', route='Main St', locality=locality,
        raw='123 Main St', latitude=37.0, longitude=-122.0
    )
    Place.objects.create(address=addr_with_coords, content_type=ct, object_id=str(org.id), organization=org)
    
    # 2. Address missing coordinates (target 1)
    addr_missing = Address.objects.create(
        street_number='456', route='Other St', locality=locality,
        raw='456 Other St'
    )
    Place.objects.create(address=addr_missing, content_type=ct, object_id=str(org.id), organization=org)
    
    # 3. Address missing coordinates but is a sibling to target 1 (same street_number, route, locality)
    addr_missing_sibling = Address.objects.create(
        street_number='456', route='Other St', locality=locality,
        raw='456 Other St Ste B'
    )
    Place.objects.create(address=addr_missing_sibling, content_type=ct, object_id=str(org.id), organization=org)
    
    # 4. Another distinct address missing coordinates (target 2)
    addr_missing_distinct = Address.objects.create(
        street_number='789', route='Another St', locality=locality,
        raw='789 Another St'
    )
    Place.objects.create(address=addr_missing_distinct, content_type=ct, object_id=str(org.id), organization=org)

    # 5. Address missing street_number and route (should be ignored by query)
    addr_no_street = Address.objects.create(
        locality=locality,
        raw='Hayward, CA'
    )
    Place.objects.create(address=addr_no_street, content_type=ct, object_id=str(org.id), organization=org)

    return {
        'with_coords': addr_with_coords,
        'missing': addr_missing,
        'missing_sibling': addr_missing_sibling,
        'missing_distinct': addr_missing_distinct,
        'no_street': addr_no_street,
    }

@pytest.mark.django_db
class TestPopulateCoordinatesCommand:

    def test_abort_if_no_api_key(self):
        """Test the command aborts immediately if GOOGLE_MAPS_API_KEY is empty."""
        original_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        settings.GOOGLE_MAPS_API_KEY = ''
        try:
            out = StringIO()
            call_command('populate_coordinates', stdout=out)
            output = out.getvalue()
            assert "GOOGLE_MAPS_API_KEY is not configured or empty. Aborting." in output
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    def test_no_addresses_missing_coordinates(self, address_setup):
        """Test the command exits early if no addresses are missing coordinates."""
        original_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'
        try:
            # Delete addresses without coordinates for this test
            address_setup['missing'].delete()
            address_setup['missing_sibling'].delete()
            address_setup['missing_distinct'].delete()

            out = StringIO()
            call_command('populate_coordinates', stdout=out)
            output = out.getvalue()

            assert "Found 0 distinct addresses missing coordinates." in output
            assert "All addresses have coordinates. Exiting." in output
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    @patch('attendees.whereabouts.management.commands.populate_coordinates.time.sleep')
    @patch('attendees.whereabouts.management.commands.populate_coordinates.CoordinatesService.geocode_address')
    def test_processes_distinct_missing_addresses(self, mock_geocode, mock_sleep, address_setup):
        """Test that the command correctly identifies distinct addresses and calls the geocode service."""
        original_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'
        try:
            # Mock geocode_address to return True for the first distinct address and False for the second
            mock_geocode.side_effect = [True, False]
            
            out = StringIO()
            call_command('populate_coordinates', sleep=0.1, stdout=out)
            output = out.getvalue()
            
            # There are 3 addresses missing coordinates, but 2 are siblings (same street, route, locality).
            # So there should only be 2 distinct addresses processed.
            assert "Found 2 distinct addresses missing coordinates." in output
            
            # Verify the service was called exactly twice (once for each distinct group)
            assert mock_geocode.call_count == 2
            
            # Verify sleep was called with our provided --sleep argument
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(0.1)
            
            # Verify output summary
            assert "Finished. Successfully geocoded 1 address groups. Failed/Skipped: 1." in output
            assert "-> Success" in output
            assert "-> Failed or Skipped" in output
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key
