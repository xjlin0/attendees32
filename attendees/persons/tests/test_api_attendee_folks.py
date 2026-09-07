import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import PermissionDenied

from attendees.persons.views.api.attendee_folks import ApiAttendeeFolksViewsSet


class TestApiAttendeeFolksViewsSet:
    @patch('attendees.persons.views.api.attendee_folks.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_folks.Attendee.objects.filter')
    @patch('attendees.persons.views.api.attendee_folks.Folk.objects.filter')
    def test_get_queryset(self, mock_folk_filter, mock_attendee_filter, mock_get_object_or_404):
        view = ApiAttendeeFolksViewsSet()
        view.request = MagicMock()
        view.kwargs = {"pk": "1"}
        view.request.query_params = {"categoryId": "1"}
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        mock_category = MagicMock()
        mock_get_object_or_404.return_value = mock_category
        
        mock_attendee = MagicMock()
        mock_attendee_filter.return_value.first.return_value = mock_attendee
        view.request.user.privileged_to_edit.return_value = True
        
        view.get_queryset()
        mock_folk_filter.assert_called()

    @patch('attendees.persons.views.api.attendee_folks.get_object_or_404')
    def test_perform_create(self, mock_get_object_or_404):
        view = ApiAttendeeFolksViewsSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        
        serializer = MagicMock()
        view.perform_create(serializer)
        
        serializer.save.assert_called_once()
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.persons.views.api.attendee_folks.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_folks.AttendingMeetService.flip_attendingmeet_by_existing_attending')
    def test_perform_update(self, mock_flip, mock_get_object_or_404):
        view = ApiAttendeeFolksViewsSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1", "HTTP_X_PRINT_DIRECTORY": "True"}
        
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        
        mock_instance = MagicMock()
        mock_instance.category_id = 0
        mock_instance.attendees.all.return_value = []
        serializer = MagicMock()
        serializer.save.return_value = mock_instance
        
        view.request.user.organization.infos.get.return_value = {'default_directory_meet': 'meet_id'}
        
        view.perform_update(serializer)
        
        serializer.save.assert_called_once()
        mock_flip.assert_called_once()
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.persons.views.api.attendee_folks.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_folks.FolkService.destroy_with_associations')
    def test_perform_destroy_success(self, mock_destroy, mock_get_object_or_404):
        view = ApiAttendeeFolksViewsSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        instance = MagicMock()
        view.perform_destroy(instance)
        
        mock_destroy.assert_called_once_with(instance, mock_target_attendee)
        mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.persons.views.api.attendee_folks.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_folks.time.sleep')
    def test_perform_destroy_permission_denied(self, mock_sleep, mock_get_object_or_404):
        view = ApiAttendeeFolksViewsSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        view.request.user.privileged_to_edit.return_value = False
        
        with pytest.raises(PermissionDenied):
            view.perform_destroy(MagicMock())
