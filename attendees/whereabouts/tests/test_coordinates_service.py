import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from address.models import Address, Locality, State, Country
from attendees.whereabouts.services.coordinates_service import CoordinatesService
from attendees.whereabouts.serializers.place_serializer import PlaceSerializer
from attendees.whereabouts.models.place import Place
from attendees.whereabouts.models.organization import Organization
from django.contrib.contenttypes.models import ContentType
from attendees.persons.models import Attendee, Attending, AttendingMeet, Folk, FolkAttendee, Category, Relation
from attendees.occasions.models import Meet, Assembly, Character
from attendees.whereabouts.models import Division
from django.contrib.auth.models import Group
import datetime
from django.utils import timezone

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

    def test_geocode_address_missing_street_number_or_route(self, address_setup):
        """Test that API is not called if address lacks street_number or route."""
        add1 = address_setup['address1']
        add1.street_number = ''
        add1.save()

        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'

        try:
            with patch('attendees.whereabouts.services.coordinates_service.requests.get') as mock_get:
                result = CoordinatesService.geocode_address(add1.id)
                assert result is False
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

    @patch('attendees.whereabouts.services.coordinates_service.requests.get')
    def test_geocode_address_api_failure_details(self, mock_get, address_setup):
        """Test handling of Google Maps API returning error status with error_message."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "error_message": "The provided API key is invalid.",
            "results": []
        }
        mock_get.return_value = mock_response

        original_key = settings.GOOGLE_MAPS_API_KEY
        settings.GOOGLE_MAPS_API_KEY = 'dummy_key'

        try:
            success, reason = CoordinatesService.geocode_address(address_setup['address1'].id, return_details=True)
            assert success is False
            assert "REQUEST_DENIED - The provided API key is invalid." in reason
        finally:
            settings.GOOGLE_MAPS_API_KEY = original_key

    def test_get_nearest_neighbors_target_not_found(self, address_setup):
        """Test get_nearest_neighbors when the target Place doesn't exist."""
        org = Organization.objects.create(slug="test-org-notfound", display_name="Test Org")
        # 9999 doesn't exist
        target, neighbors = CoordinatesService.get_nearest_neighbors(9999, org)
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
        
        target, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id, org)
        assert target is None
        assert list(neighbors) == []

    def test_get_nearest_neighbors_success(self, address_setup):
        """Test get_nearest_neighbors successfully calculates distance and orders results using real PostGIS queries."""
        folk_category, _ = Category.objects.get_or_create(id=0, defaults={"type": "folk", "display_name": "folk"})
        attending_category, _ = Category.objects.get_or_create(id=25, defaults={"type": "attending", "display_name": "attending"})
        Relation.objects.get_or_create(id=0, defaults={"title": "self", "gender": "unspecified"})
        org = Organization.objects.create(slug="test-org-succ", display_name="Test Org Succ")
        auth_group = Group.objects.create(name="test-group-succ")
        div = Division.objects.create(organization=org, slug="div-succ", display_name="Div Succ", audience_auth_group=auth_group, infos={"acronym": "SU"})
        
        ctype_org = ContentType.objects.get_for_model(Organization)
        ctype_att = ContentType.objects.get_for_model(Attendee)
        
        # Target place: San Francisco (approx)
        addr1 = address_setup['address1']
        addr1.latitude = 37.7749
        addr1.longitude = -122.4194
        addr1.save()
        target_place = Place.objects.create(
            content_type=ctype_org, object_id=str(org.id), organization=org,
            address=addr1, display_name="Target SF"
        )
        
        att_oak = Attendee.objects.create(first_name="Oak", last_name="Land", division=div, gender="male")
        att_sj = Attendee.objects.create(first_name="San", last_name="Jose", division=div, gender="male")
        
        # Neighbor 1: Oakland (approx 8.5 miles away)
        addr2 = address_setup['address2']
        addr2.latitude = 37.8044
        addr2.longitude = -122.2712
        addr2.save()
        neighbor_oakland = Place.objects.create(
            content_type=ctype_att, object_id=str(att_oak.id), organization=org,
            address=addr2, display_name="Oakland"
        )
        
        # Neighbor 2: San Jose (approx 42 miles away)
        addr3 = address_setup['address3']
        addr3.latitude = 37.3382
        addr3.longitude = -121.8863
        addr3.save()
        neighbor_sj = Place.objects.create(
            content_type=ctype_att, object_id=str(att_sj.id), organization=org,
            address=addr3, display_name="San Jose"
        )
        
        # Another place without coordinates (should be ignored)
        addr_no_coords = Address.objects.create(raw="No coords", locality=addr1.locality)
        Place.objects.create(
            content_type=ctype_att, object_id=str(att_oak.id), organization=org,
            address=addr_no_coords, display_name="No Coords"
        )
        
        target, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id, org)
        
        assert target == target_place
        assert len(neighbors) == 2
        
        # Because we're using real PostGIS calculations now, Oakland should be index 0, San Jose index 1
        assert neighbors[0].id == neighbor_oakland.id
        assert neighbors[1].id == neighbor_sj.id
        
        # Distance should be annotated and accurately calculated
        assert hasattr(neighbors[0], 'distance_miles')
        assert hasattr(neighbors[1], 'distance_miles')
        
        # SF to Oakland is roughly 8-10 miles
        assert 8.0 < neighbors[0].distance_miles < 10.0
        # SF to SJ is roughly 40-50 miles
        assert 40.0 < neighbors[1].distance_miles < 50.0

    def test_get_nearest_neighbors_with_meets_filter(self, address_setup):
        """Test get_nearest_neighbors correctly filters results by meets parameter."""
        now = timezone.now()
        
        folk_category = Category.objects.create(id=0, type="folk", display_name="folk")
        attending_category = Category.objects.create(id=25, type="attending", display_name="attending")
        assembly_category = Category.objects.create(id=33, type="assembly", display_name="assembly")
        Relation.objects.create(id=0, title="self", gender="unspecified")
        
        org = Organization.objects.create(slug="test-org", display_name="Test Org")
        auth_group = Group.objects.create(name="test-group")
        div = Division.objects.create(organization=org, slug="test-div", display_name="Test Div", audience_auth_group=auth_group)
        assembly = Assembly.objects.create(division=div, slug="test-assembly", display_name="Test Assembly", category=assembly_category)
        character = Character.objects.create(assembly=assembly, slug="test-char", display_name="Test Char")
        
        ct = ContentType.objects.get_for_model(Organization)
        meet_a = Meet.objects.create(assembly=assembly, slug="meet-a", display_name="Meet A", start=now, finish=now + datetime.timedelta(days=1), site_type=ct, site_id=org.id)
        meet_b = Meet.objects.create(assembly=assembly, slug="meet-b", display_name="Meet B", start=now, finish=now + datetime.timedelta(days=1), site_type=ct, site_id=org.id)
        
        # Setup coordinates for 3 places
        addr1 = address_setup['address1']
        addr1.latitude, addr1.longitude = 37.7749, -122.4194  # SF (Target)
        addr1.save()
        
        addr2 = address_setup['address2']
        addr2.latitude, addr2.longitude = 37.8044, -122.2712  # Oakland (Attendee in Meet A)
        addr2.save()
        
        addr3 = address_setup['address3']
        addr3.latitude, addr3.longitude = 37.3382, -121.8863  # SJ (Folk containing Attendee in Meet B)
        addr3.save()
        
        # Create Attendees
        attendee_target = Attendee.objects.create(first_name="Target", last_name="SF", division=div, gender="male")
        attendee_a = Attendee.objects.create(first_name="Attendee A", last_name="Oak", division=div, gender="male")
        attendee_b = Attendee.objects.create(first_name="Attendee B", last_name="SJ", division=div, gender="male")
        
        # Attendings
        attending_target = Attending.objects.create(attendee=attendee_target, category=attending_category)
        attending_a = Attending.objects.create(attendee=attendee_a, category=attending_category)
        attending_b = Attending.objects.create(attendee=attendee_b, category=attending_category)
        
        # AttendingMeets
        AttendingMeet.objects.create(attending=attending_target, meet=meet_a, character=character, category=attending_category, start=now, finish=now + datetime.timedelta(days=1))
        AttendingMeet.objects.create(attending=attending_a, meet=meet_a, character=character, category=attending_category, start=now, finish=now + datetime.timedelta(days=1))
        AttendingMeet.objects.create(attending=attending_b, meet=meet_b, character=character, category=attending_category, start=now, finish=now + datetime.timedelta(days=1))
        
        # Folk
        folk_b = Folk.objects.create(division=div)
        FolkAttendee.objects.create(folk=folk_b, attendee=attendee_b, role_id=0)
        
        # Places
        attendee_ct = ContentType.objects.get_for_model(Attendee)
        folk_ct = ContentType.objects.get_for_model(Folk)
        
        target_place = Place.objects.create(
            content_type=attendee_ct, object_id=str(attendee_target.id), organization=org,
            address=addr1, display_name="Target SF"
        )
        neighbor_oakland = Place.objects.create(
            content_type=attendee_ct, object_id=str(attendee_a.id), organization=org,
            address=addr2, display_name="Oakland"
        )
        neighbor_sj = Place.objects.create(
            content_type=folk_ct, object_id=str(folk_b.id), organization=org,
            address=addr3, display_name="San Jose"
        )
        
        # Query with meet-a (Should return Oakland only)
        _, neighbors_a = CoordinatesService.get_nearest_neighbors(target_place.id, org, meets=['meet-a'])
        assert len(neighbors_a) == 1
        assert neighbors_a[0] == neighbor_oakland
        
        # Query with meet-b (Should return San Jose only)
        _, neighbors_b = CoordinatesService.get_nearest_neighbors(target_place.id, org, meets=['meet-b'])
        assert len(neighbors_b) == 1
        assert neighbors_b[0] == neighbor_sj
        
        # Query with both
        _, neighbors_both = CoordinatesService.get_nearest_neighbors(target_place.id, org, meets=['meet-a', 'meet-b'])
        assert len(neighbors_both) == 2

    def test_get_nearest_neighbors_folk_husband_wife_filtering(self, address_setup):
        """
        Test husband and wife belonging to the same Folk family sharing one Place.
        When only the wife participates in the filtered meet, only her attendee_id
        and attendee_name are returned, ignoring the husband even if his display_order is smaller.
        """
        now = timezone.now()
        folk_category, _ = Category.objects.get_or_create(id=0, defaults={"type": "folk", "display_name": "folk"})
        attending_category, _ = Category.objects.get_or_create(id=25, defaults={"type": "attending", "display_name": "attending"})
        assembly_category, _ = Category.objects.get_or_create(id=33, defaults={"type": "assembly", "display_name": "assembly"})
        Relation.objects.get_or_create(id=0, defaults={"title": "self", "gender": "unspecified"})
        Relation.objects.get_or_create(id=1, defaults={"title": "spouse", "gender": "unspecified"})

        org = Organization.objects.create(slug="test-org-hw", display_name="Test Org HW")
        auth_group = Group.objects.create(name="test-group-hw")
        div = Division.objects.create(organization=org, slug="div-hw", display_name="Div HW", audience_auth_group=auth_group, infos={"acronym": "HW"})
        assembly = Assembly.objects.create(division=div, slug="assembly-hw", display_name="Assembly HW", category=assembly_category)
        ct_org = ContentType.objects.get_for_model(Organization)
        meet = Meet.objects.create(assembly=assembly, slug="meet-hw", display_name="Meet HW", start=now, finish=now + datetime.timedelta(days=1), site_type=ct_org, site_id=org.id)
        character = Character.objects.create(assembly=assembly, slug="char-hw", display_name="Char HW")

        addr_target = address_setup['address1']
        addr_target.latitude = 37.7749
        addr_target.longitude = -122.4194
        addr_target.save()

        addr_family = address_setup['address2']
        addr_family.latitude = 37.8044
        addr_family.longitude = -122.2712
        addr_family.save()

        # Target attendee
        attendee_target = Attendee.objects.create(first_name="Target", last_name="User", division=div, gender="male", infos={"names": {"original": "Target User"}})
        attending_target = Attending.objects.create(attendee=attendee_target, category=attending_category)
        AttendingMeet.objects.create(attending=attending_target, meet=meet, character=character, category=attending_category, start=now, finish=now + datetime.timedelta(days=1))

        # Husband and Wife
        husband = Attendee.objects.create(first_name="Husband", last_name="Smith", division=div, gender="male", infos={"names": {"original": "Husband Smith"}})
        wife = Attendee.objects.create(first_name="Wife", last_name="Smith", division=div, gender="female", infos={"names": {"original": "Wife Smith"}})

        # Both belong to same Folk (Family)
        family_folk = Folk.objects.create(division=div, category=folk_category)
        FolkAttendee.objects.create(folk=family_folk, attendee=husband, role_id=0, display_order=0)
        FolkAttendee.objects.create(folk=family_folk, attendee=wife, role_id=1, display_order=1)

        # Only Wife attends the meet
        attending_wife = Attending.objects.create(attendee=wife, category=attending_category)
        AttendingMeet.objects.create(attending=attending_wife, meet=meet, character=character, category=attending_category, start=now, finish=now + datetime.timedelta(days=1))

        attendee_ct = ContentType.objects.get_for_model(Attendee)
        folk_ct = ContentType.objects.get_for_model(Folk)

        target_place = Place.objects.create(
            content_type=attendee_ct, object_id=str(attendee_target.id), organization=org,
            address=addr_target, display_name="Target Residence"
        )
        family_place = Place.objects.create(
            content_type=folk_ct, object_id=str(family_folk.id), organization=org,
            address=addr_family, display_name="Smith Family Residence"
        )

        target, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id, org, meets=['meet-hw'])

        assert len(neighbors) == 1
        neighbor = neighbors[0]
        assert str(neighbor.object_id) == str(family_folk.id)

        serializer_data = PlaceSerializer(neighbor).data
        assert serializer_data['attendee_id'] == str(wife.id)
        assert serializer_data['attendee_name'] == "HW Wife Smith"

    def test_get_nearest_neighbors_without_meets_excludes_soft_deleted_and_expired(self, address_setup):
        """
        Verify that even when meets is not provided, soft-deleted place, soft-deleted folk/attendee,
        and expired family members are completely excluded from neighbors.
        """
        folk_category, _ = Category.objects.get_or_create(id=0, defaults={"type": "folk", "display_name": "folk"})
        attending_category, _ = Category.objects.get_or_create(id=25, defaults={"type": "attending", "display_name": "attending"})
        Relation.objects.get_or_create(id=0, defaults={"title": "self", "gender": "unspecified"})

        org = Organization.objects.create(slug="org-exc", display_name="Org Excl")
        auth_group = Group.objects.create(name="grp-exc")
        div = Division.objects.create(organization=org, slug="div-exc", display_name="Div Excl", audience_auth_group=auth_group, infos={"acronym": "EX"})

        addr_target = address_setup['address1']
        addr_target.latitude = 37.7749
        addr_target.longitude = -122.4194
        addr_target.save()

        addr_neighbor = address_setup['address2']
        addr_neighbor.latitude = 37.8044
        addr_neighbor.longitude = -122.2712
        addr_neighbor.save()

        attendee_ct = ContentType.objects.get_for_model(Attendee)
        folk_ct = ContentType.objects.get_for_model(Folk)
        org_ct = ContentType.objects.get_for_model(Organization)

        # Target place
        target_place = Place.objects.create(
            content_type=org_ct, object_id=str(org.id), organization=org,
            address=addr_target, display_name="Center Place"
        )

        # 1. Non-person place (Organization place) should be ignored
        Place.objects.create(
            content_type=org_ct, object_id=str(org.id), organization=org,
            address=addr_neighbor, display_name="Org Bldg"
        )

        # 2. Soft-deleted Place should be ignored
        active_attendee = Attendee.objects.create(first_name="Active", last_name="User", division=div, gender="unspecified")
        Place.objects.create(
            content_type=attendee_ct, object_id=str(active_attendee.id), organization=org,
            address=addr_neighbor, display_name="Deleted Place", is_removed=True
        )

        # 3. Place pointing to soft-deleted Attendee should be ignored
        deleted_attendee = Attendee.objects.create(first_name="Deleted", last_name="Person", division=div, gender="unspecified", is_removed=True)
        Place.objects.create(
            content_type=attendee_ct, object_id=str(deleted_attendee.id), organization=org,
            address=addr_neighbor, display_name="Deleted Attendee Place", is_removed=False
        )

        # 4. Place pointing to Folk with only expired members should be ignored
        expired_folk = Folk.objects.create(division=div, category=folk_category)
        expired_attendee = Attendee.objects.create(first_name="Expired", last_name="Member", division=div, gender="unspecified")
        past_date = datetime.date.today() - datetime.timedelta(days=30)
        FolkAttendee.objects.create(folk=expired_folk, attendee=expired_attendee, role_id=0, finish=past_date)
        Place.objects.create(
            content_type=folk_ct, object_id=str(expired_folk.id), organization=org,
            address=addr_neighbor, display_name="Expired Folk Place"
        )

        # 5. Valid active folk place (should be returned!)
        valid_folk = Folk.objects.create(division=div, category=folk_category)
        valid_attendee = Attendee.objects.create(first_name="Valid", last_name="Person", division=div, gender="unspecified", infos={"names": {"original": "Valid Person"}})
        FolkAttendee.objects.create(folk=valid_folk, attendee=valid_attendee, role_id=0, finish=None)
        valid_place = Place.objects.create(
            content_type=folk_ct, object_id=str(valid_folk.id), organization=org,
            address=addr_neighbor, display_name="Valid Folk Place"
        )

        _, neighbors = CoordinatesService.get_nearest_neighbors(target_place.id, org, meets=[])
        assert len(neighbors) == 1
        assert neighbors[0].id == valid_place.id
        assert neighbors[0].target_attendee_id == str(valid_attendee.id)
        assert neighbors[0].target_attendee_name == "EX Valid Person"
