import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import PermissionDenied

from attendees.persons.views.api.attendee_attendings import ApiAttendeeAttendingsViewSet


class TestApiAttendeeAttendingsViewSet:
    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_attendings.Attending.objects.filter')
    def test_get_queryset_success(self, mock_filter, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.kwargs = {}
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        view.request.query_params = {}
        
        target_attendee = MagicMock()
        target_attendee.id = 1
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.organization = MagicMock()
        view.request.user.attendee = target_attendee
        
        result = view.get_queryset()
        mock_filter.assert_called()

    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_attendings.time.sleep')
    def test_get_queryset_permission_denied(self, mock_sleep, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.kwargs = {}
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        target_attendee = MagicMock()
        target_attendee.id = 2
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.organization = MagicMock()
        view.request.user.attendee = MagicMock()
        view.request.user.privileged_to_edit.return_value = False
        view.request.user.attendee.can_schedule_attendee.return_value = False
        
        with pytest.raises(PermissionDenied):
            view.get_queryset()
        mock_sleep.assert_called_once_with(2)

    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    def test_perform_update_success(self, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        target_attendee = MagicMock()
        target_attendee.id = 1
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        serializer = MagicMock()
        view.perform_update(serializer)
        
        serializer.save.assert_called_once()
        target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_attendings.time.sleep')
    def test_perform_update_permission_denied(self, mock_sleep, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        target_attendee = MagicMock()
        target_attendee.id = 1
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.privileged_to_edit.return_value = False
        serializer = MagicMock()
        
        with pytest.raises(PermissionDenied):
            view.perform_update(serializer)

    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    def test_perform_create_success(self, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        target_attendee = MagicMock()
        target_attendee.id = 1
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        serializer = MagicMock()
        view.perform_create(serializer)
        
        serializer.save.assert_called_once_with(attendee=target_attendee)
        target_attendee.save.assert_called_once_with(update_fields=['modified'])

    @patch('attendees.persons.views.api.attendee_attendings.get_object_or_404')
    @patch('attendees.persons.views.api.attendee_attendings.AttendingService.destroy_with_associations')
    def test_perform_destroy_success(self, mock_destroy, mock_get_object_or_404):
        view = ApiAttendeeAttendingsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        target_attendee = MagicMock()
        target_attendee.id = 1
        mock_get_object_or_404.return_value = target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        instance = MagicMock()
        view.perform_destroy(instance)
        
        mock_destroy.assert_called_once_with(instance)
        target_attendee.save.assert_called_once_with(update_fields=['modified'])
