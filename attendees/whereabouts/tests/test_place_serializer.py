import pytest
from unittest.mock import patch, MagicMock
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

    @patch('attendees.persons.models.FolkAttendee')
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
        
        mock_folk_attendee.objects.filter.return_value.order_by.return_value.first.return_value = mock_query_result

        serializer = PlaceSerializer(mock_place)
        
        assert serializer.data['attendee_id'] == 'winner-attendee-uuid'
        # Verify the query was built correctly
        mock_folk_attendee.objects.filter.assert_called_with(folk_id='999e4567-e89b-12d3-a456-426614174000')

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
        
        # Scenario 1: distance_miles is present
        mock_place.distance_miles = 1.2345
        serializer1 = PlaceSerializer(mock_place)
        assert serializer1.data['distance'] == "1.2 miles"

        # Scenario 2: distance_miles is explicitly None
        mock_place.distance_miles = None
        serializer2 = PlaceSerializer(mock_place)
        assert serializer2.data['distance'] is None

        # Scenario 3: distance_miles attribute doesn't exist at all
        del mock_place.distance_miles
        serializer3 = PlaceSerializer(mock_place)
        assert serializer3.data['distance'] is None
