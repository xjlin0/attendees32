import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import AuthenticationFailed
from django.db.models import Q

from attendees.whereabouts.views.api.user_places import ApiUserPlaceViewSet

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.organization = MagicMock()
    return user

@pytest.fixture
def mock_request(mock_user):
    request = MagicMock()
    request.user = mock_user
    request.query_params = {}
    return request

class TestApiUserPlaceViewSet:

    @patch('attendees.whereabouts.views.api.user_places.Place')
    def test_get_queryset_with_place_id_privileged(self, mock_place, mock_request):
        view = ApiUserPlaceViewSet()
        mock_request.query_params = {"id": "42"}
        mock_request.user.privileged.return_value = True
        view.request = mock_request
        
        queryset = view.get_queryset()
        
        mock_place.objects.filter.assert_called_once_with(
            pk="42",
            organization=mock_request.user.organization
        )
        assert queryset == mock_place.objects.filter.return_value

    @patch('attendees.whereabouts.views.api.user_places.Place')
    def test_get_queryset_with_place_id_unprivileged(self, mock_place, mock_request):
        view = ApiUserPlaceViewSet()
        mock_request.query_params = {"id": "42"}
        mock_request.user.privileged.return_value = False
        view.request = mock_request
        
        queryset = view.get_queryset()
        
        mock_request.user.attendee.contacts.filter.assert_called_once_with(
            pk="42",
            organization=mock_request.user.organization
        )
        assert queryset == mock_request.user.attendee.contacts.filter.return_value

    @patch('attendees.whereabouts.views.api.user_places.Place')
    def test_get_queryset_with_search_value(self, mock_place, mock_request):
        view = ApiUserPlaceViewSet()
        mock_request.query_params = {"searchValue": "test keyword"}
        mock_request.user.privileged.return_value = True
        view.request = mock_request
        
        queryset = view.get_queryset()
        
        expected_q = (
            Q(address__street_number__icontains="test keyword")
            | Q(display_name__icontains="test keyword")
            | Q(address__route__icontains="test keyword")
            | Q(address__raw__icontains="test keyword")
        )
        
        mock_place.objects.filter.assert_called_once()
        args, kwargs = mock_place.objects.filter.call_args
        
        assert len(args) == 1
        assert args[0] == expected_q
        assert kwargs == {"organization": mock_request.user.organization}
        
        assert queryset == mock_place.objects.filter.return_value

    @patch('attendees.whereabouts.views.api.user_places.time.sleep')
    def test_get_queryset_no_organization(self, mock_sleep, mock_request):
        view = ApiUserPlaceViewSet()
        mock_request.user.organization = None
        view.request = mock_request
        
        with pytest.raises(AuthenticationFailed) as excinfo:
            view.get_queryset()
            
        assert "Have your account assigned an organization?" in str(excinfo.value)
        mock_sleep.assert_called_once_with(2)
