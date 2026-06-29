import pytest
from unittest.mock import MagicMock, patch
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from attendees.persons.views.api.organization_meet_character_attendingmeets import ApiOrganizationMeetCharacterAttendingMeetsViewSet

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.organization = MagicMock()
    user.can_see_all_organizational_meets_attendees.return_value = True
    user.attendee.scheduling_attendees.return_value = []
    user.belongs_to_groups_of.return_value = True
    return user

@pytest.fixture
def mock_request(mock_user):
    request = MagicMock()
    request.user = mock_user
    # Using a MagicMock for query_params to handle getlist easily
    request.query_params = MagicMock()
    request.query_params.get.side_effect = lambda key, default=None: {
        "group": '[{"selector":"meet","desc":false,"isExpanded":false}]',
        "filter": '[[null]]',
        "sort": '[{"selector":"meet","desc":false},{"selector":"start","desc":false}]'
    }.get(key, default)
    request.query_params.getlist.return_value = []
    return request

@pytest.fixture
def view(mock_request):
    view = ApiOrganizationMeetCharacterAttendingMeetsViewSet()
    view.request = mock_request
    view.kwargs = {}
    return view

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.AttendingMeet")
@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.Utility")
def test_list_with_grouping(mock_utility, mock_am, view):
    view.filter_queryset = MagicMock()
    view.get_queryset = MagicMock()
    view.paginate_queryset = MagicMock()
    view.paginate_queryset.return_value = ["mock_item"]
    
    mock_utility.group_count.return_value = {"data": "group_count_result"}
    
    mock_qs = MagicMock()
    mock_am.objects.filter.return_value = mock_qs
    mock_qs.values.return_value.order_by.return_value.annotate.return_value = "counters"
    
    # We also mock Response since it returns Response directly
    with patch("attendees.persons.views.api.organization_meet_character_attendingmeets.Response") as mock_response:
        mock_response.return_value = "response"
        response = view.list(view.request)
        
        mock_utility.group_count.assert_called_once_with("meet", "counters")
        assert response == "response"

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.Utility")
def test_list_without_grouping(mock_utility, view):
    view.request.query_params.get.side_effect = lambda key, default=None: {
        "filter": '[[null]]'
    }.get(key, default)
    
    view.filter_queryset = MagicMock()
    view.get_queryset = MagicMock()
    view.paginate_queryset = MagicMock()
    view.paginate_queryset.return_value = ["mock_item"]
    
    view.get_serializer = MagicMock()
    view.get_serializer.return_value.data = "serialized_data"
    
    mock_utility.transform_result.return_value = "transformed_result"
    view.get_paginated_response = MagicMock(return_value="paginated_response")
    
    response = view.list(view.request)
    
    mock_utility.transform_result.assert_called_once_with("serialized_data", None)
    view.get_paginated_response.assert_called_once_with("transformed_result")
    assert response == "paginated_response"

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.AttendingMeet")
def test_get_queryset_with_pk(mock_am, view):
    view.kwargs = {"pk": "1"}
    
    qs = view.get_queryset()
    
    mock_am.objects.filter.assert_called_once()
    assert qs == mock_am.objects.filter.return_value

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.AttendingMeetService")
def test_get_queryset_without_pk(mock_am_service, view):
    qs = view.get_queryset()
    
    mock_am_service.by_organization_meet_characters.assert_called_once()
    assert qs == mock_am_service.by_organization_meet_characters.return_value

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.time.sleep")
def test_get_queryset_no_organization(mock_sleep, view, mock_user):
    mock_user.organization = None
    
    with pytest.raises(AuthenticationFailed):
        view.get_queryset()
        
    mock_sleep.assert_called_once_with(2)

def test_perform_create(view):
    mock_serializer = MagicMock()
    mock_instance = MagicMock()
    mock_serializer.save.return_value = mock_instance
    
    view.perform_create(mock_serializer)
    
    mock_serializer.save.assert_called_once()
    mock_instance.attending.attendee.save.assert_called_once_with(update_fields=['modified'])

def test_perform_update(view):
    mock_serializer = MagicMock()
    mock_instance = MagicMock()
    mock_serializer.save.return_value = mock_instance
    
    view.perform_update(mock_serializer)
    
    mock_serializer.save.assert_called_once()
    mock_instance.attending.attendee.save.assert_called_once_with(update_fields=['modified'])

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.Attendance")
@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.Utility")
def test_perform_destroy(mock_utility, mock_attendance, view):
    mock_instance = MagicMock()
    mock_instance.meet.infos = {'allowed_groups': ['some_group', 'organization_participant']}
    mock_utility.now_with_timezone.return_value = "now"
    
    view.perform_destroy(mock_instance)
    
    view.request.user.belongs_to_groups_of.assert_called_once_with(['some_group'])
    mock_attendance.objects.filter.assert_called_once_with(
        gathering__meet=mock_instance.meet,
        gathering__start__gte="now",
        attending=mock_instance.attending
    )
    mock_attendance.objects.filter.return_value.delete.assert_called_once()
    mock_instance.delete.assert_called_once()
    mock_instance.attending.attendee.save.assert_called_once_with(update_fields=['modified'])

@patch("attendees.persons.views.api.organization_meet_character_attendingmeets.time.sleep")
def test_perform_destroy_permission_denied(mock_sleep, view):
    view.request.user.belongs_to_groups_of.return_value = False
    mock_instance = MagicMock()
    mock_instance.meet.infos = {'allowed_groups': ['some_group']}
    
    with pytest.raises(PermissionDenied):
        view.perform_destroy(mock_instance)
        
    mock_sleep.assert_called_once_with(2)
