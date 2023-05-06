import time

from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse

from attendees.users.models import Menu


class RouteGuard(UserPassesTestMixin):
    """
    check if the user are among auth groups that can visit the url
    """

    def test_func(self):
        whether_user_allowed_to_read_the_page = Menu.objects.filter(
            auth_groups__in=self.request.user.groups.all(),
            url_name=self.request.resolver_match.url_name,
            menuauthgroup__read=True,
            is_removed=False,
        ).exists()
        if not whether_user_allowed_to_read_the_page:
            time.sleep(2)

        return whether_user_allowed_to_read_the_page

    def handle_no_permission(self):
        """Show warning info so user can know what happened"""
        return HttpResponse(
            "Is menu.url_name correct? You groups does not have permissions to visit such route!"
        )


class SpyGuard(UserPassesTestMixin):
    """
    check if the user can visit urls for checking other attendee's data
    """

    def test_func(self):  # Superusers can still access such attendee in admin UI
        targeting_attendee_id = self.request.META.get(
            "HTTP_X_TARGET_ATTENDEE_ID", self.kwargs.get("attendee_id")
        )
        current_attendee = self.request.user.attendee if hasattr(self.request.user, 'attendee') else None

        if targeting_attendee_id == "new":
            return Menu.user_can_create_attendee(
                self.request.user
            )  # create nonfamily attendee is attendee_create_view
        if targeting_attendee_id:
            if current_attendee:
                if str(current_attendee.id) == targeting_attendee_id:
                    return True  # self.request.resolver_match.url_name == Menu.ATTENDEE_UPDATE_VIEW # for make spy guard only allows self/new at certian view
                if current_attendee.under_same_org_with(targeting_attendee_id):
                    return (
                        self.request.user.can_see_all_organizational_meets_attendees()
                        or current_attendee.can_schedule_attendee(targeting_attendee_id)
                    )
        else:
            return self.request.resolver_match.url_name == Menu.ATTENDEE_UPDATE_SELF

        time.sleep(2)
        return False

    def handle_no_permission(self):
        """Show warning info so user can know what happened"""
        return HttpResponse(
            "Do you have attendee associated with your user? You do not have permissions to visit this!",
            status=403,
        )


class RouteAndSpyGuard(UserPassesTestMixin):
    def test_func(self):
        return RouteGuard.test_func(self) and SpyGuard.test_func(self)
