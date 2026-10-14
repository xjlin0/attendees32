from unittest.mock import MagicMock, patch

from django.db.models import Case

from attendees.occasions.views.api.user_assembly_meets import ApiUserAssemblyMeetsViewSet


@patch("attendees.occasions.views.api.user_assembly_meets.AttendingMeet")
@patch("attendees.occasions.views.api.user_assembly_meets.Meet")
@patch("attendees.occasions.views.api.user_assembly_meets.get_object_or_404")
def test_target_attendees_own_meets_sort_first(mock_get_object, mock_meet, mock_am):
    """The attendee page's participation grid names its rows from the first
    page of this endpoint only, so the attendee's own meets must lead and
    assembly name may only order within each group."""
    view = ApiUserAssemblyMeetsViewSet()
    view.request = MagicMock()
    view.request.query_params.get.return_value = None
    view.request.query_params.getlist.return_value = []
    view.kwargs = {}

    view.get_queryset()

    order_by = mock_meet.objects.filter.return_value.annotate.return_value.order_by
    args = order_by.call_args.args
    assert isinstance(args[0], Case)
    assert args[1] == "assembly_name"
