import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework.test import APIClient
from attendees.users.models import User
from attendees.whereabouts.models import Place, Organization
from address.models import Address

@pytest.fixture
def api_client():
    client = APIClient()
    org = Organization.objects.create(slug="test_org", display_name="Test Org")
    user = User.objects.create(username="testuser", email="test@example.com", organization=org)
    client.force_login(user)
    return client

@pytest.mark.django_db
class TestUpdateSpatialAPIView:

    @patch('attendees.whereabouts.views.api.update_spatial.Place')
    def test_post_success(self, mock_place, api_client):
        # Setup mock place and address
        mock_instance = MagicMock()
        mock_instance.address = MagicMock()
        mock_instance.address.id = 999
        mock_place.objects.select_related.return_value.get.return_value = mock_instance

        with patch('attendees.whereabouts.views.api.update_spatial.GeocodingService.geocode_address') as mock_geocode:
            mock_geocode.return_value = True
            
            url = reverse('whereabouts:update_spatial', kwargs={'pk': '123'})
            response = api_client.post(url)
            
            assert response.status_code == 200
            assert response.data['detail'] == "Address coordinates updated successfully."
            mock_geocode.assert_called_once_with(999)

    @patch('attendees.whereabouts.views.api.update_spatial.Place.objects.select_related')
    def test_post_place_not_found(self, mock_select_related, api_client):
        mock_select_related.return_value.get.side_effect = Place.DoesNotExist
        
        url = reverse('whereabouts:update_spatial', kwargs={'pk': '999'})
        response = api_client.post(url)
        
        assert response.status_code == 404
        assert response.data['detail'] == "Place not found."

    @patch('attendees.whereabouts.views.api.update_spatial.Place.objects.select_related')
    def test_post_no_address(self, mock_select_related, api_client):
        mock_instance = MagicMock()
        mock_instance.address = None
        mock_select_related.return_value.get.return_value = mock_instance

        url = reverse('whereabouts:update_spatial', kwargs={'pk': '123'})
        response = api_client.post(url)
        
        assert response.status_code == 400
        assert response.data['detail'] == "Place has no associated address."
