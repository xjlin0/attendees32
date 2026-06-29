import pytest
from unittest.mock import patch, MagicMock

from attendees.persons.views.api.datagrid_data_attendee import ApiDatagridDataAttendeeViewSet


class TestApiDatagridDataAttendeeViewSet:
    @patch('attendees.persons.views.api.datagrid_data_attendee.Attendee.objects.annotate')
    def test_get_queryset_with_pk(self, mock_annotate):
        view = ApiDatagridDataAttendeeViewSet()
        view.request = MagicMock()
        view.kwargs = {"pk": "1"}
        view.request.query_params = {}
        
        mock_qs = MagicMock()
        mock_annotate.return_value.filter.return_value = mock_qs
        
        view.get_queryset()
        
        mock_annotate.assert_called_once()
        mock_qs.filter.assert_called_once()

    @patch('attendees.persons.views.api.datagrid_data_attendee.Attendee.objects.filter')
    def test_get_queryset_with_term(self, mock_filter):
        view = ApiDatagridDataAttendeeViewSet()
        view.request = MagicMock()
        view.kwargs = {}
        view.request.query_params = {"searchValue": "term"}
        
        mock_qs = MagicMock()
        mock_filter.return_value = mock_qs
        
        view.get_queryset()
        
        mock_filter.assert_called_once()
        mock_qs.filter.assert_called_once()

    @patch('attendees.persons.views.api.datagrid_data_attendee.Meet.objects.filter')
    @patch('attendees.persons.views.api.datagrid_data_attendee.Folk.objects.create')
    @patch('attendees.persons.views.api.datagrid_data_attendee.FolkAttendee.objects.create')
    @patch('attendees.persons.views.api.datagrid_data_attendee.get_object_or_404')
    @patch('attendees.persons.views.api.datagrid_data_attendee.AttendingMeetService.flip_attendingmeet_by_existing_attending')
    def test_perform_create(self, mock_flip, mock_get_object_or_404, mock_fa_create, mock_folk_create, mock_meet_filter):
        view = ApiDatagridDataAttendeeViewSet()
        view.request = MagicMock()
        view.request.META = {
            "HTTP_X_ADD_FOLK": "new",
            "HTTP_X_FOLK_ROLE": "1",
            "HTTP_X_JOIN_MEET": "1",
            "HTTP_X_JOIN_CHARACTER": "char",
            "HTTP_X_JOIN_GATHERING": ""
        }
        
        serializer = MagicMock()
        instance = MagicMock()
        instance.last_name = "Smith"
        instance.infos = {"names": {"original": "John"}}
        serializer.save.return_value = instance
        
        mock_meet = MagicMock()
        mock_meet.assembly.division.organization = view.request.user.organization
        mock_meet_filter.return_value.first.return_value = mock_meet
        
        mock_folk = MagicMock()
        mock_folk.id = 1
        mock_folk_create.return_value = mock_folk
        
        view.perform_create(serializer)
        
        serializer.save.assert_called_once()
        mock_folk_create.assert_called_once()
        mock_fa_create.assert_called_once()
        mock_flip.assert_called_once()

    @patch('attendees.persons.views.api.datagrid_data_attendee.get_object_or_404')
    @patch('attendees.persons.views.api.datagrid_data_attendee.AttendeeService.end_all_activities')
    @patch('attendees.persons.views.api.datagrid_data_attendee.AttendeeService.add_past')
    def test_perform_update(self, mock_add_past, mock_end_activities, mock_get_object_or_404):
        view = ApiDatagridDataAttendeeViewSet()
        view.request = MagicMock()
        view.request.COOKIES = {"timezone": "UTC"}
        view.request.META = {
            "HTTP_X_TARGET_ATTENDEE_ID": "1",
            "HTTP_X_END_ALL_ATTENDEE_ACTIVITIES": "True",
            "HTTP_X_ADD_PAST": "past_id"
        }
        
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        serializer = MagicMock()
        instance = MagicMock()
        serializer.save.return_value = instance
        
        view.perform_update(serializer)
        
        serializer.save.assert_called_once()
        mock_end_activities.assert_called_once_with(instance, view.request.user.attendee_uuid_str())
        mock_add_past.assert_called_once()

    @patch('attendees.persons.views.api.datagrid_data_attendee.get_object_or_404')
    @patch('attendees.persons.views.api.datagrid_data_attendee.AttendeeService.destroy_with_associations')
    def test_perform_destroy(self, mock_destroy, mock_get_object_or_404):
        view = ApiDatagridDataAttendeeViewSet()
        view.request = MagicMock()
        view.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
        
        mock_target_attendee = MagicMock()
        mock_get_object_or_404.return_value = mock_target_attendee
        
        view.request.user.privileged_to_edit.return_value = True
        
        instance = MagicMock()
        view.perform_destroy(instance)
        
        mock_destroy.assert_called_once_with(instance)
