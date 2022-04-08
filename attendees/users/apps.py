import pghistory
from django.apps import AppConfig
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "attendees.users"
    verbose_name = _("Users")

    def ready(self):
        user_model = get_user_model()
        # permission_model = django_apps.get_model("auth.Permission", require_ready=False)
        group_model = django_apps.get_model("auth.Group", require_ready=False)

        pghistory.track(
            pghistory.Snapshot('group.snapshot'),
            app_label='users'
        )(group_model)

        pghistory.track(  # Track events to user group relationships
            pghistory.AfterInsert('group.add'),
            pghistory.BeforeDelete('group.remove'),
            obj_fk=None,
            app_label='users',
        )(user_model.groups.through)

        pghistory.track(  # Track events to user group relationships
            pghistory.AfterInsert('user_permission.add'),
            pghistory.BeforeDelete('user_permission.remove'),
            obj_fk=None,
            app_label='users',
        )(user_model.user_permissions.through)

        try:
            import attendees.users.signals  # noqa F401
        except ImportError:
            pass
