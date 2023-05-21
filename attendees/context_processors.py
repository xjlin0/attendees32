from django.contrib import messages
from pytz import timezone
from datetime import datetime
from django.conf import settings
from urllib import parse
from attendees.users.models import Menu


def common_variables(request):  # TODO move organization info to view
    tzname = request.COOKIES.get('timezone') or settings.CLIENT_DEFAULT_TIME_ZONE
    user_organization_name = settings.PROJECT_NAME
    user_organization_name_slug = '0_organization_slug'
    user_organization = request.user.organization if hasattr(request.user, 'organization') else None
    user_attendee_id = request.user.attendee_uuid_str() if hasattr(request.user, 'attendee_uuid_str') else None  # Anonymous User does not have attendee_uuid_str, also could be different when admin browser others
    main_menus = Menu.objects.filter(
        auth_groups__in=request.user.groups.all(),
        category='main',
        menuauthgroup__read=True,
        organization=user_organization,
        is_removed=False,
    ).distinct()

    if not user_attendee_id and request.user.is_authenticated:
        messages.add_message(request, messages.WARNING, "No attendee assigned to your account, most pages won't work!!!")

    if request.user.is_authenticated and user_organization:
        user_organization = request.user.organization
        user_organization_name = user_organization.infos.get('acronym') or user_organization.display_name
        user_organization_name_slug = user_organization.slug
    return {
        'timezone_name': datetime.now(timezone(parse.unquote(tzname))).tzname(),
        'user_organization_name': user_organization_name,
        'user_organization_name_slug': user_organization_name_slug,
        'user_api_allowed_url_name': {name: True for name in request.user.allowed_url_names()} if hasattr(request.user, 'allowed_url_names') else {},
        'user_attendee_id': user_attendee_id,
        'main_menus': main_menus,
    }
