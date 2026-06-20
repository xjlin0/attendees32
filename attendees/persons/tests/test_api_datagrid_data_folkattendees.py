import pytest
from unittest.mock import MagicMock, patch
from django.db.models import Q
from attendees.persons.views.api.datagrid_data_folkattendees import ApiDatagridDataFolkAttendeesViewsSet
from attendees.persons.models import Attendee, Past


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.privileged_to_edit.return_value = True
    user.is_counselor.return_value = False
    user.is_a.return_value = False
    user.privileged.return_value = True
    user.attendee_uuid_str.return_value = "1234-5678"
    user.organization.infos = {'settings': {'default_directory_meet': 1}}
    return user


@pytest.fixture
def mock_request(mock_user):
    request = MagicMock()
    request.user = mock_user
    request.META = {"HTTP_X_TARGET_ATTENDEE_ID": "1"}
    request.query_params = {}
    return request


@pytest.fixture
def view(mock_request):
    view = ApiDatagridDataFolkAttendeesViewsSet()
    view.request = mock_request
    view.kwargs = {}
    return view


@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.FolkAttendee")
def test_get_queryset_counselor_with_category(mock_folkattendee, mock_get_object_or_404, view, mock_user):
    mock_user.is_counselor.return_value = True
    mock_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_attendee
    view.request.query_params["categoryId"] = "1"
    
    mock_qs = MagicMock()
    mock_folkattendee.objects = mock_qs

    qs = view.get_queryset()
    
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    assert qs is not None


@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.FolkAttendee")
def test_get_queryset_coworker_family_category(mock_folkattendee, mock_get_object_or_404, view, mock_user):
    mock_user.is_counselor.return_value = False
    mock_user.is_a.return_value = True  # is coworker
    mock_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_attendee
    view.request.query_params["categoryId"] = "0"
    
    mock_qs = MagicMock()
    mock_folkattendee.objects = mock_qs

    qs = view.get_queryset()
    
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    assert qs is not None


@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.FolkAttendee")
def test_get_queryset_coworker_other_category(mock_folkattendee, mock_get_object_or_404, view, mock_user):
    mock_user.is_counselor.return_value = False
    mock_user.is_a.return_value = True  # is coworker
    mock_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_attendee
    view.request.query_params["categoryId"] = "25"
    
    mock_qs = MagicMock()
    mock_folkattendee.objects = mock_qs

    qs = view.get_queryset()
    
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    assert qs is not None


@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.FolkAttendee")
def test_get_queryset_ordinary_user(mock_folkattendee, mock_get_object_or_404, view, mock_user):
    mock_user.is_counselor.return_value = False
    mock_user.is_a.return_value = False
    mock_user.privileged_to_edit.return_value = False
    mock_user.privileged.return_value = False
    
    mock_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_attendee
    view.request.query_params["categoryId"] = "0"
    
    mock_qs = MagicMock()
    mock_user.attendee.folkattendee_set = mock_qs

    qs = view.get_queryset()
    
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    assert qs is not None


@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.FolkAttendee")
def test_get_queryset_with_pk(mock_folkattendee, mock_get_object_or_404, view, mock_user):
    mock_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_attendee
    view.kwargs["pk"] = "123"
    
    mock_qs = MagicMock()
    mock_folkattendee.objects = mock_qs

    qs = view.get_queryset()
    
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    assert qs is not None


@patch("attendees.persons.views.api.datagrid_data_folkattendees.AttendingMeetService")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.Utility")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
def test_perform_update(mock_get_object_or_404, mock_utility, mock_attending_meet_service, view):
    mock_serializer = MagicMock()
    mock_instance = MagicMock()
    mock_instance.folk.infos = {'print_directory': True}
    mock_instance.folk.category_id = Attendee.FAMILY_CATEGORY
    mock_serializer.save.return_value = mock_instance
    
    mock_target_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_target_attendee
    
    view.perform_update(mock_serializer)
    
    mock_serializer.save.assert_called_once()
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])
    mock_instance.folk.save.assert_called_once_with(update_fields=['modified'])
    mock_utility.add_update_attendee_in_infos.assert_called_once_with(mock_instance, "1234-5678")
    mock_attending_meet_service.flip_attendingmeet_by_existing_attending.assert_called_once_with(
        view.request.user, [mock_instance.attendee], 1, True
    )


@patch("attendees.persons.views.api.datagrid_data_folkattendees.AttendingMeetService")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.Utility")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
def test_perform_create(mock_get_object_or_404, mock_utility, mock_attending_meet_service, view):
    mock_serializer = MagicMock()
    mock_instance = MagicMock()
    mock_instance.folk.infos = {'print_directory': False}
    mock_instance.folk.category_id = Attendee.FAMILY_CATEGORY
    mock_serializer.save.return_value = mock_instance
    
    mock_target_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_target_attendee
    
    view.perform_create(mock_serializer)
    
    mock_serializer.save.assert_called_once()
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])
    mock_instance.folk.save.assert_called_once_with(update_fields=['modified'])
    mock_utility.add_update_attendee_in_infos.assert_called_once_with(mock_instance, "1234-5678")
    mock_attending_meet_service.flip_attendingmeet_by_existing_attending.assert_called_once_with(
        view.request.user, [mock_instance.attendee], 1, False
    )


@patch("attendees.persons.views.api.datagrid_data_folkattendees.Utility")
@patch("attendees.persons.views.api.datagrid_data_folkattendees.get_object_or_404")
def test_perform_destroy(mock_get_object_or_404, mock_utility, view):
    mock_instance = MagicMock()
    mock_target_attendee = MagicMock()
    mock_get_object_or_404.return_value = mock_target_attendee
    mock_folk = mock_instance.folk
    
    view.perform_destroy(mock_instance)
    
    mock_utility.add_update_attendee_in_infos.assert_called_once_with(mock_instance, "1234-5678")
    mock_get_object_or_404.assert_called_once_with(Attendee, pk="1")
    mock_instance.delete.assert_called_once()
    mock_target_attendee.save.assert_called_once_with(update_fields=['modified'])
    mock_folk.save.assert_called_once_with(update_fields=['modified'])
