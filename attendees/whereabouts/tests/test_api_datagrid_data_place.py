import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import PermissionDenied

from attendees.whereabouts.views.api.datagrid_data_place import ApiDatagridDataPlaceViewSet

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.organization = MagicMock()
    return user

@pytest.fixture
def mock_request(mock_user):
    request = MagicMock()
    request.user = mock_user
    request.META = {}
    return request

class TestApiDatagridDataPlaceViewSet:

    @patch('attendees.whereabouts.views.api.datagrid_data_place.PlaceSerializer')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.Place')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.Response')
    def test_retrieve(self, mock_response, mock_place, mock_serializer, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        view.kwargs = {"pk": 1}
        
        mock_place_instance = MagicMock()
        mock_place.objects.filter.return_value.first.return_value = mock_place_instance
        
        mock_serializer_instance = MagicMock()
        mock_serializer_instance.data = {"id": 1, "name": "Test"}
        mock_serializer.return_value = mock_serializer_instance
        
        response = view.retrieve(mock_request)
        
        mock_place.objects.filter.assert_called_once_with(pk=1, organization=mock_request.user.organization)
        mock_serializer.assert_called_once_with(mock_place_instance)
        mock_response.assert_called_once_with({"id": 1, "name": "Test"})
        assert response == mock_response.return_value

    @patch('attendees.whereabouts.views.api.datagrid_data_place.Place')
    def test_get_queryset(self, mock_place, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        view.request = mock_request
        view.kwargs = {"pk": 42}
        
        queryset = view.get_queryset()
        
        mock_place.objects.filter.assert_called_once_with(pk=42, organization=mock_request.user.organization)
        assert queryset == mock_place.objects.filter.return_value

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.CoordinatesService')
    def test_perform_update_privileged_no_lat(self, mock_coords_service, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = True
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_serializer = MagicMock()
        mock_instance = MagicMock()
        mock_instance.address.latitude = None
        mock_instance.subject = MagicMock()
        mock_serializer.save.return_value = mock_instance
        
        view.perform_update(mock_serializer)
        
        mock_get_object_or_404.assert_called_once()
        mock_request.user.privileged_to_edit.assert_called_once_with("123")
        mock_serializer.save.assert_called_once()
        mock_coords_service.geocode_address.assert_called_once_with(mock_instance.address.id)
        mock_instance.subject.save.assert_called_once_with(update_fields=['modified'])
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.time.sleep')
    def test_perform_update_unprivileged(self, mock_sleep, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = False
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_serializer = MagicMock()
        
        with pytest.raises(PermissionDenied) as excinfo:
            view.perform_update(mock_serializer)
            
        assert "Not allowed to update Place" in str(excinfo.value)
        mock_sleep.assert_called_once_with(2)

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.CoordinatesService')
    def test_perform_create_privileged(self, mock_coords_service, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = True
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_serializer = MagicMock()
        mock_instance = MagicMock()
        mock_instance.address.longitude = None
        mock_instance.subject = MagicMock()
        mock_serializer.save.return_value = mock_instance
        
        view.perform_create(mock_serializer)
        
        mock_serializer.save.assert_called_once_with(organization=mock_request.user.organization)
        mock_coords_service.geocode_address.assert_called_once_with(mock_instance.address.id)
        mock_instance.subject.save.assert_called_once_with(update_fields=['modified'])
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.time.sleep')
    def test_perform_create_unprivileged(self, mock_sleep, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = False
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_serializer = MagicMock()
        
        with pytest.raises(PermissionDenied) as excinfo:
            view.perform_create(mock_serializer)
            
        assert "Not allowed to create Place" in str(excinfo.value)
        mock_sleep.assert_called_once_with(2)

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    def test_perform_destroy_privileged(self, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = True
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_instance = MagicMock()
        mock_instance.subject = MagicMock()
        
        view.perform_destroy(mock_instance)
        
        mock_instance.delete.assert_called_once()
        mock_instance.subject.save.assert_called_once_with(update_fields=['modified'])
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.whereabouts.views.api.datagrid_data_place.get_object_or_404')
    @patch('attendees.whereabouts.views.api.datagrid_data_place.time.sleep')
    def test_perform_destroy_unprivileged(self, mock_sleep, mock_get_object_or_404, mock_request):
        view = ApiDatagridDataPlaceViewSet()
        mock_request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "123"}
        mock_request.user.privileged_to_edit.return_value = False
        view.request = mock_request
        
        mock_target_attendee = MagicMock()
        mock_target_attendee.id = "123"
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_instance = MagicMock()
        
        with pytest.raises(PermissionDenied) as excinfo:
            view.perform_destroy(mock_instance)
            
        assert "Not allowed to delete Place" in str(excinfo.value)
        mock_sleep.assert_called_once_with(2)
