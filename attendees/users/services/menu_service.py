from attendees.users.models import Menu


class MenuService:
    @staticmethod
    def is_user_allowed_to_write(request):
        return Menu.objects.filter(
            auth_groups__in=request.user.groups.all(),
            url_name=request.resolver_match.url_name,
            menuauthgroup__write=True,
            is_removed=False,
        ).exists()
