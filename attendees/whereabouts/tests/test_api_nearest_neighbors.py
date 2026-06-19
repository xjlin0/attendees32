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

    @patch('attendees.whereabouts.views.api.nearest_neighbors.CoordinatesService')
    def test_get_nearest_neighbors_success(self, mock_coords_service, api_client):
        # Mock the target place resolution and neighbors
        mock_target_place = MagicMock()
        mock_neighbor = MagicMock()
        
        mock_coords_service.get_nearest_neighbors.return_value = (mock_target_place, [mock_neighbor])
        
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

    @patch('attendees.whereabouts.views.api.nearest_neighbors.CoordinatesService')
    def test_get_no_target_coordinates(self, mock_coords_service, api_client):
        mock_coords_service.get_nearest_neighbors.return_value = (None, [])
        
        url = reverse('whereabouts:nearest_neighbors', kwargs={'pk': 'user-uuid-123'})
        response = api_client.get(url)
        
        assert response.status_code == 404
        assert "No valid coordinates found" in response.data['detail']

    @patch('attendees.whereabouts.views.api.nearest_neighbors.CoordinatesService')
    def test_get_database_error(self, mock_coords_service, api_client):
        mock_coords_service.get_nearest_neighbors.side_effect = Exception("DB Connection Error")
        
        url = reverse('whereabouts:nearest_neighbors', kwargs={'pk': 'user-uuid-123'})
        response = api_client.get(url)
        
        assert response.status_code == 500
        assert "Error processing request" in response.data['detail']
