import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from attendees.users.models import User
from attendees.whereabouts.models import Organization

@pytest.fixture
def api_client():
    client = APIClient()
    org = Organization.objects.create(slug="test_org_n", display_name="Test Org N")
    user = User.objects.create(username="testuser_neighbors", email="test_n@example.com", organization=org)
    client.force_login(user)
    return client

@pytest.mark.django_db
class TestNearestNeighborsAPIView:

    @patch('attendees.whereabouts.views.api.nearest_neighbors.Place')
    def test_get_nearest_neighbors_success(self, mock_place_model, api_client):
        # Mock the target place resolution
        mock_target_place = MagicMock()
        mock_target_place.id = '123'
        mock_target_place.address.latitude = 37.0
        mock_target_place.address.longitude = -122.0
        
        # Setup the chain: Place.objects.select_related().filter().first()
        mock_place_model.objects.select_related.return_value.filter.return_value.first.return_value = mock_target_place
        
        # Mock the neighbors queryset chain
        # .annotate().exclude().order_by()[:top_n]
        mock_neighbor = MagicMock()
        mock_neighbor.distance_miles = 1.5
        # The serializer will expect a proper Place object or a mock that behaves like one.
        # It's easier to mock the Serializer entirely to avoid complex data structure requirements.
        
        with patch('attendees.whereabouts.views.api.nearest_neighbors.PlaceSerializer') as mock_serializer:
            mock_serializer.return_value.data = [
                {
                    "distance": "1.5 miles",
                    "id": "456",
                    "display_name": "Neighbor Place",
                    "attendee_id": "789"
                }
            ]
            
            url = reverse('whereabouts:nearest_neighbors', kwargs={'pk': 'user-uuid-123'})
            response = api_client.get(url, {'top': 10})
            
            assert response.status_code == 200
            assert response.data['totalCount'] == 1
            assert len(response.data['data']) == 1
            assert response.data['data'][0]['distance'] == "1.5 miles"
            assert response.data['data'][0]['place']['display_name'] == "Neighbor Place"

    @patch('attendees.whereabouts.views.api.nearest_neighbors.Place')
    def test_get_no_target_coordinates(self, mock_place_model, api_client):
        # Simulate target place not having coordinates (filter().first() returns None)
        mock_place_model.objects.select_related.return_value.filter.return_value.first.return_value = None
        
        url = reverse('whereabouts:nearest_neighbors', kwargs={'pk': 'user-uuid-123'})
        response = api_client.get(url)
        
        assert response.status_code == 404
        assert "No valid coordinates found" in response.data['detail']

    @patch('attendees.whereabouts.views.api.nearest_neighbors.Place')
    def test_get_database_error(self, mock_place_model, api_client):
        # Simulate a database error
        mock_place_model.objects.select_related.side_effect = Exception("DB Connection Error")
        
        url = reverse('whereabouts:nearest_neighbors', kwargs={'pk': 'user-uuid-123'})
        response = api_client.get(url)
        
        assert response.status_code == 500
        assert "Error processing request" in response.data['detail']
