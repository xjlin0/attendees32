from rest_framework.permissions import BasePermission

from attendees.users.authorization.route_guard import spy_guard_allows


class DrfSpyGuard(BasePermission):
    """
    SpyGuard as a DRF permission, for API viewsets that token-authenticated
    clients must be able to call.

    Django-level guards (UserPassesTestMixin, login_required) run in dispatch()
    before DRF authenticates, so a request with a valid ``Authorization: Token``
    header is still anonymous when they check it and is redirected to the login
    page. A DRF permission runs after authentication, so session and token
    requests are treated alike. The rules are SpyGuard's own (spy_guard_allows).
    """

    message = "Do you have attendee associated with your user? You do not have permissions to visit this!"

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return spy_guard_allows(
            request.user,
            request.META.get("HTTP_X_TARGET_ATTENDEE_ID", view.kwargs.get("attendee_id")),
            request.resolver_match.url_name,
        )
