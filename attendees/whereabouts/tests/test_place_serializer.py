import pytest
import datetime
from unittest.mock import patch, MagicMock
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.division import Division
from attendees.whereabouts.models.place import Place
from attendees.persons.models import Attendee, Folk, FolkAttendee, Category, Relation
from address.models import Address, Locality, State, Country
from attendees.whereabouts.serializers.place_serializer import PlaceSerializer


@pytest.mark.django_db
class TestPlaceSerializer:

    def test_attendee_id_resolves_from_attendee(self):
        # Mock Place instance linked to an Attendee
        mock_place = MagicMock()
        mock_place.content_type.model = 'attendee'
        mock_place.object_id = '123e4567-e89b-12d3-a456-426614174000'
        mock_place.distance_miles = None
        mock_place.address = None

        serializer = PlaceSerializer(mock_place)
        
        # Verify it just returns the object_id directly
        assert serializer.data['attendee_id'] == '123e4567-e89b-12d3-a456-426614174000'

    @patch('attendees.whereabouts.serializers.place_serializer.FolkAttendee')
    def test_attendee_id_resolves_from_folk_using_display_order(self, mock_folk_attendee):
        # Mock Place instance linked to a Folk
        mock_place = MagicMock()
        mock_place.content_type.model = 'folk'
        mock_place.object_id = '999e4567-e89b-12d3-a456-426614174000'
        mock_place.distance_miles = None
        mock_place.address = None

        # Mock the Django ORM query chain: FolkAttendee.objects.filter().order_by().first()
        mock_query_result = MagicMock()
        mock_query_result.attendee_id = 'winner-attendee-uuid'
        mock_query_result.attendee.division.infos = {"acronym": "MCK"}
        mock_query_result.attendee.infos = {"names": {"original": "Mock Winner"}}
        
        mock_folk_attendee.objects.filter.return_value.order_by.return_value.first.return_value = mock_query_result
        mock_folk_attendee.objects.select_related.return_value.filter.return_value.order_by.return_value.first.return_value = mock_query_result

        serializer = PlaceSerializer(mock_place)
        
        assert serializer.data['attendee_id'] == 'winner-attendee-uuid'
        assert serializer.data['attendee_name'] == 'MCK Mock Winner'
        # Verify the query was built correctly with valid filters
        _, kwargs = mock_folk_attendee.objects.filter.call_args
        assert kwargs['folk_id'] == '999e4567-e89b-12d3-a456-426614174000'
        assert kwargs['is_removed'] is False

    def test_attendee_id_with_unrelated_content_type(self):
        mock_place = MagicMock()
        mock_place.content_type.model = 'organization'
        mock_place.object_id = 1
        mock_place.distance_miles = None
        mock_place.address = None

        serializer = PlaceSerializer(mock_place)
        assert serializer.data['attendee_id'] is None

    def test_distance_serialization(self):
        mock_place = MagicMock()
        mock_place.content_type.model = 'attendee'
        mock_place.object_id = '123'
        mock_place.address = None
        
        # Scenario 1: distance_miles is present but no azimuth
        mock_place.distance_miles = 1.2345
        mock_place.azimuth = None
        serializer1 = PlaceSerializer(mock_place)
        assert serializer1.data['distance'] == "1.2 miles"

        # Scenario 1.5: distance_miles and azimuth are present
        mock_place.distance_miles = 1.2345
        mock_place.azimuth = 3.14159  # roughly 180 degrees (South)
        serializer1_5 = PlaceSerializer(mock_place)
        assert serializer1_5.data['distance'] == "1.2 miles S"

        # Scenario 2: distance_miles is explicitly None
        mock_place.distance_miles = None
        serializer2 = PlaceSerializer(mock_place)
        assert serializer2.data['distance'] is None

        # Scenario 3: distance_miles attribute doesn't exist at all
        del mock_place.distance_miles
        serializer3 = PlaceSerializer(mock_place)
        assert serializer3.data['distance'] is None

    def test_attendee_id_and_name_from_target_attributes(self):
        mock_place = MagicMock()
        mock_place.content_type.model = 'folk'
        mock_place.__dict__['target_attendee_id'] = 'cached-attendee-uuid'
        mock_place.__dict__['target_attendee_name'] = 'DEV Jane Doe'
        mock_place.distance_miles = None
        mock_place.address = None

        serializer = PlaceSerializer(mock_place)
        assert serializer.data['attendee_id'] == 'cached-attendee-uuid'
        assert serializer.data['attendee_name'] == 'DEV Jane Doe'

    def test_attendee_id_resolves_from_folk_with_real_db_filtering(self):
        """
        Integration test referencing test_place setup:
        Verify fallback query filters out inactive/removed family members (Husband display_order=0)
        and resolves to active member (Wife display_order=1).
        """
        folk_category, _ = Category.objects.get_or_create(id=0, defaults={"type": "folk", "display_name": "folk"})
        attending_category, _ = Category.objects.get_or_create(id=25, defaults={"type": "attending", "display_name": "attending"})
        Relation.objects.get_or_create(id=0, defaults={"title": "self", "gender": "unspecified"})
        Relation.objects.get_or_create(id=1, defaults={"title": "spouse", "gender": "unspecified"})

        org = Organization.objects.create(slug="ser-org", display_name="Serializer Org")
        auth_group = Group.objects.create(name="ser-group")
        div = Division.objects.create(organization=org, slug="ser-div", display_name="Serializer Div", audience_auth_group=auth_group, infos={"acronym": "SR"})
        country = Country.objects.create(name="USA", code="US")
        state = State.objects.create(name="California", code="CA", country=country)
        locality = Locality.objects.create(name="Hayward", postal_code="94541", state=state)
        address = Address.objects.create(raw="456 Elm St", locality=locality)

        husband = Attendee.objects.create(first_name="Husband", last_name="Old", division=div, gender="male", infos={"names": {"original": "Husband Old"}})
        wife = Attendee.objects.create(first_name="Wife", last_name="Active", division=div, gender="female", infos={"names": {"original": "Wife Active"}})

        family_folk = Folk.objects.create(division=div, category=folk_category)
        past_date = datetime.date.today() - datetime.timedelta(days=10)
        FolkAttendee.objects.create(folk=family_folk, attendee=husband, role_id=0, display_order=0, finish=past_date)
        FolkAttendee.objects.create(folk=family_folk, attendee=wife, role_id=1, display_order=1, finish=None)

        folk_ct = ContentType.objects.get_for_model(Folk)
        place = Place.objects.create(
            content_type=folk_ct,
            object_id=str(family_folk.id),
            organization=org,
            address=address,
            display_name="Family Residence",
            display_order=1,
        )

        serializer = PlaceSerializer(place)
        data = serializer.data
        assert data['attendee_id'] == str(wife.id)
        assert data['attendee_name'] == "SR Wife Active"
