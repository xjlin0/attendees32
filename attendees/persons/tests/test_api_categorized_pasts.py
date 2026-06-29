import pytest
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import PermissionDenied

from attendees.persons.views.api.categorized_pasts import ApiCategorizedPastsViewSet


class TestApiCategorizedPastsViewSet:
    @patch('attendees.persons.views.api.categorized_pasts.MenuAuthGroup.objects.filter')
    @patch('attendees.persons.views.api.categorized_pasts.get_object_or_404')
    def test_get_queryset_success(self, mock_get_object_or_404, mock_menu_filter):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.kwargs = {"pk": "1"}
        view.request.query_params = {"category__type": "test"}
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        mock_menu_filter.return_value.exists.return_value = True
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        view.request.user.is_counselor.return_value = True
        view.request.user.attendee_uuid_str.return_value = "123"
        
        view.get_queryset()
        mock_target_attendee.pasts.filter.assert_called()

    @patch('attendees.persons.views.api.categorized_pasts.MenuAuthGroup.objects.filter')
    @patch('attendees.persons.views.api.categorized_pasts.time.sleep')
    def test_get_queryset_permission_denied(self, mock_sleep, mock_menu_filter):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.kwargs = {"pk": "1"}
        view.request.query_params = {"category__type": "test"}
        mock_menu_filter.return_value.exists.return_value = False
        
        with pytest.raises(PermissionDenied):
            view.get_queryset()

    @patch('attendees.persons.views.api.categorized_pasts.time.sleep')
    def test_perform_destroy_permission_denied(self, mock_sleep):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.request.user.privileged_to_edit.return_value = False
        
        with pytest.raises(PermissionDenied):
            view.perform_destroy(MagicMock())

    def test_perform_destroy_success(self):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        view.request.user.privileged_to_edit.return_value = True
        
        instance = MagicMock()
        view.perform_destroy(instance)
        
        instance.delete.assert_called_once()
        instance.subject.save.assert_called_once_with(update_fields=['modified'])

    def test_perform_update_success(self):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        view.request.user.privileged_to_edit.return_value = True
        
        serializer = MagicMock()
        instance = MagicMock()
        serializer.save.return_value = instance
        
        view.perform_update(serializer)
        
        serializer.save.assert_called_once()
        instance.subject.save.assert_called_once_with(update_fields=['modified'])

    def test_perform_create_success(self):
        view = ApiCategorizedPastsViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        view.request.user.privileged_to_edit.return_value = True
        
        serializer = MagicMock()
        instance = MagicMock()
        serializer.save.return_value = instance
        
        view.perform_create(serializer)
        
        serializer.save.assert_called_once_with(organization=view.request.user.organization)
        instance.subject.save.assert_called_once_with(update_fields=['modified'])
