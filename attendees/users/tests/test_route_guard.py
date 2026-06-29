import pytest
from unittest.mock import MagicMock, patch
from django.http import HttpResponse

from attendees.users.authorization.route_guard import (
    RouteGuard,
    SpyGuard,
    RouteAndSpyGuard,
)


class TestRouteGuard:
    @patch("attendees.users.authorization.route_guard.time.sleep")
    @patch("attendees.users.authorization.route_guard.Menu")
    def test_test_func_allowed(self, mock_menu, mock_sleep):
        guard = RouteGuard()
        guard.request = MagicMock()
        guard.request.user.groups.all.return_value = ["group1"]
        guard.request.resolver_match.url_name = "test_url"

        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_menu.objects.filter.return_value = mock_qs

        result = guard.test_func()

        assert result is True
        mock_menu.objects.filter.assert_called_once_with(
            auth_groups__in=["group1"],
            url_name="test_url",
            menuauthgroup__read=True,
            is_removed=False,
        )
        mock_sleep.assert_not_called()

    @patch("attendees.users.authorization.route_guard.time.sleep")
    @patch("attendees.users.authorization.route_guard.Menu")
    def test_test_func_not_allowed(self, mock_menu, mock_sleep):
        guard = RouteGuard()
        guard.request = MagicMock()
        guard.request.user.groups.all.return_value = ["group1"]
        guard.request.resolver_match.url_name = "test_url"

        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_menu.objects.filter.return_value = mock_qs

        result = guard.test_func()

        assert result is False
        mock_sleep.assert_called_once_with(2)

    def test_handle_no_permission(self):
        guard = RouteGuard()
        response = guard.handle_no_permission()
        assert isinstance(response, HttpResponse)
        assert b"groups does not have permissions" in response.content


class TestSpyGuard:
    def setup_guard(self, meta_target=None, kwarg_target=None, current_attendee=None):
        guard = SpyGuard()
        guard.request = MagicMock()
        guard.kwargs = {}
        if meta_target is not None:
            guard.request.META = {"HTTP_X_TARGET_ATTENDEE_ID": meta_target}
        else:
            guard.request.META = {}
            if kwarg_target is not None:
                guard.kwargs["attendee_id"] = kwarg_target

        if current_attendee is not None:
            guard.request.user.attendee = current_attendee
        else:
            mock_user = MagicMock()
            del mock_user.attendee
            guard.request.user = mock_user

        return guard

    @patch("attendees.users.authorization.route_guard.Menu")
    def test_test_func_new_attendee(self, mock_menu):
        guard = self.setup_guard(meta_target="new")
        mock_menu.user_can_create_attendee.return_value = True

        assert guard.test_func() is True
        mock_menu.user_can_create_attendee.assert_called_once_with(guard.request.user)

    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_self_attendee(self, mock_sleep):
        current_attendee = MagicMock()
        current_attendee.id = 123
        guard = self.setup_guard(meta_target="123", current_attendee=current_attendee)

        assert guard.test_func() is True
        mock_sleep.assert_not_called()

    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_same_org_can_see_all(self, mock_sleep):
        current_attendee = MagicMock()
        current_attendee.id = 123
        current_attendee.under_same_org_with.return_value = True
        guard = self.setup_guard(meta_target="456", current_attendee=current_attendee)
        guard.request.user.can_see_all_organizational_meets_attendees.return_value = True

        assert guard.test_func() is True
        current_attendee.under_same_org_with.assert_called_once_with("456")

    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_same_org_can_schedule(self, mock_sleep):
        current_attendee = MagicMock()
        current_attendee.id = 123
        current_attendee.under_same_org_with.return_value = True
        current_attendee.can_schedule_attendee.return_value = True
        guard = self.setup_guard(meta_target="456", current_attendee=current_attendee)
        guard.request.user.can_see_all_organizational_meets_attendees.return_value = False

        assert guard.test_func() is True
        current_attendee.can_schedule_attendee.assert_called_once_with("456")

    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_same_org_cannot_access(self, mock_sleep):
        current_attendee = MagicMock()
        current_attendee.id = 123
        current_attendee.under_same_org_with.return_value = True
        current_attendee.can_schedule_attendee.return_value = False
        guard = self.setup_guard(meta_target="456", current_attendee=current_attendee)
        guard.request.user.can_see_all_organizational_meets_attendees.return_value = False

        assert guard.test_func() is False
        mock_sleep.assert_not_called()

    @patch("attendees.users.authorization.route_guard.Menu")
    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_no_targeting_id_matches_update_self(self, mock_sleep, mock_menu):
        guard = self.setup_guard()
        mock_menu.ATTENDEE_UPDATE_SELF = "update_self"
        guard.request.resolver_match.url_name = "update_self"

        assert guard.test_func() is True
        mock_sleep.assert_not_called()

    @patch("attendees.users.authorization.route_guard.Menu")
    @patch("attendees.users.authorization.route_guard.time.sleep")
    def test_test_func_no_targeting_id_mismatches_update_self(self, mock_sleep, mock_menu):
        guard = self.setup_guard()
        mock_menu.ATTENDEE_UPDATE_SELF = "update_self"
        guard.request.resolver_match.url_name = "other_view"

        assert guard.test_func() is False
        mock_sleep.assert_not_called()

    def test_handle_no_permission(self):
        guard = SpyGuard()
        response = guard.handle_no_permission()
        assert isinstance(response, HttpResponse)
        assert response.status_code == 403
        assert b"permissions to visit this" in response.content


class TestRouteAndSpyGuard:
    @patch("attendees.users.authorization.route_guard.SpyGuard.test_func")
    @patch("attendees.users.authorization.route_guard.RouteGuard.test_func")
    def test_test_func_both_true(self, mock_route, mock_spy):
        guard = RouteAndSpyGuard()
        mock_route.return_value = True
        mock_spy.return_value = True

        assert guard.test_func() is True
        mock_route.assert_called_once_with(guard)
        mock_spy.assert_called_once_with(guard)

    @patch("attendees.users.authorization.route_guard.SpyGuard.test_func")
    @patch("attendees.users.authorization.route_guard.RouteGuard.test_func")
    def test_test_func_route_false(self, mock_route, mock_spy):
        guard = RouteAndSpyGuard()
        mock_route.return_value = False

        assert guard.test_func() is False
        mock_route.assert_called_once_with(guard)
        mock_spy.assert_not_called()

    @patch("attendees.users.authorization.route_guard.SpyGuard.test_func")
    @patch("attendees.users.authorization.route_guard.RouteGuard.test_func")
    def test_test_func_spy_false(self, mock_route, mock_spy):
        guard = RouteAndSpyGuard()
        mock_route.return_value = True
        mock_spy.return_value = False

        assert guard.test_func() is False
        mock_route.assert_called_once_with(guard)
        mock_spy.assert_called_once_with(guard)
