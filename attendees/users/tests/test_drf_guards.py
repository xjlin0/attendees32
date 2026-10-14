from unittest.mock import MagicMock, patch

from attendees.users.authorization.drf_guards import DrfSpyGuard


def _request(authenticated=True, header=None):
    request = MagicMock()
    request.user.is_authenticated = authenticated
    request.META = {"HTTP_X_TARGET_ATTENDEE_ID": header} if header else {}
    request.resolver_match.url_name = "some_url"
    return request


def test_an_anonymous_request_is_refused():
    view = MagicMock(kwargs={})
    assert DrfSpyGuard().has_permission(_request(authenticated=False), view) is False


@patch("attendees.users.authorization.drf_guards.spy_guard_allows", return_value=True)
def test_the_target_header_is_checked_with_spy_guard_rules(mock_allows):
    request = _request(header="target-id")
    view = MagicMock(kwargs={"attendee_id": "ignored-when-header-present"})

    assert DrfSpyGuard().has_permission(request, view) is True
    mock_allows.assert_called_once_with(request.user, "target-id", "some_url")


@patch("attendees.users.authorization.drf_guards.spy_guard_allows", return_value=False)
def test_the_url_attendee_id_is_used_without_a_header(mock_allows):
    request = _request()
    view = MagicMock(kwargs={"attendee_id": "url-id"})

    assert DrfSpyGuard().has_permission(request, view) is False
    mock_allows.assert_called_once_with(request.user, "url-id", "some_url")
