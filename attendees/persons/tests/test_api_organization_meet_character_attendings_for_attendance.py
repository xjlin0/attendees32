import pytest
from unittest.mock import MagicMock, patch
from rest_framework.exceptions import AuthenticationFailed
from attendees.persons.views.api.organization_meet_character_attendings_for_attendance import ApiOrganizationMeetCharacterAttendingsViewSetForAttendance

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.organization = MagicMock()
    user.can_see_all_organizational_meets_attendees.return_value = True
    user.attendee.scheduling_attendees.return_value = []
    return user

@pytest.fixture
def mock_request(mock_user):
    request = MagicMock()
    request.user = mock_user
    request.query_params = MagicMock()
    request.query_params.get.side_effect = lambda key, default=None: {
        "searchValue": "",
        "searchExpr": "",
        "searchOperation": "",
        "sort": '[{"selector":"gathering.meet","desc":false},{"selector":"start","desc":false}]'
    }.get(key, default)
    return request

@pytest.fixture
def view(mock_request):
    view = ApiOrganizationMeetCharacterAttendingsViewSetForAttendance()
    view.request = mock_request
    view.kwargs = {}
    return view

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Utility")
def test_list_paginated(mock_utility, view):
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

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Utility")
def test_list_unpaginated(mock_utility, view):
    view.filter_queryset = MagicMock()
    view.get_queryset = MagicMock()
    view.paginate_queryset = MagicMock()
    view.paginate_queryset.return_value = None
    
    view.get_serializer = MagicMock()
    view.get_serializer.return_value.data = "serialized_data"
    
    mock_utility.transform_result.return_value = "transformed_result"
    
    with patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Response") as mock_response:
        mock_response.return_value = "response"
        response = view.list(view.request)
        
        mock_utility.transform_result.assert_called_once_with("serialized_data", None)
        mock_response.assert_called_once_with("transformed_result")
        assert response == "response"

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Attending")
def test_get_queryset_with_pk(mock_attending, view):
    view.kwargs = {"pk": "1"}
    
    qs = view.get_queryset()
    
    mock_attending.objects.filter.assert_called_once()
    mock_attending.objects.filter.return_value.distinct.assert_called_once()
    assert qs == mock_attending.objects.filter.return_value.distinct.return_value

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Attending")
def test_get_queryset_without_pk(mock_attending, view):
    qs = view.get_queryset()
    
    mock_attending.objects.filter.assert_called_once()
    mock_attending.objects.filter.return_value.order_by.assert_called_once_with("attendee__last_name")
    assert qs == mock_attending.objects.filter.return_value.order_by.return_value

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.Attending")
def test_get_queryset_without_pk_with_search(mock_attending, view):
    view.request.query_params.get.side_effect = lambda key, default=None: {
        "searchValue": "test_search",
        "searchExpr": "attending_label",
        "searchOperation": "contains",
    }.get(key, default)
    
    qs = view.get_queryset()
    
    mock_attending.objects.filter.assert_called_once()
    mock_attending.objects.filter.return_value.order_by.assert_called_once_with("attendee__last_name")
    assert qs == mock_attending.objects.filter.return_value.order_by.return_value

@patch("attendees.persons.views.api.organization_meet_character_attendings_for_attendance.time.sleep")
def test_get_queryset_no_organization(mock_sleep, view, mock_user):
    mock_user.organization = None
    
    with pytest.raises(AuthenticationFailed):
        view.get_queryset()
        
    mock_sleep.assert_called_once_with(2)
