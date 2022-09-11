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
        group_model = django_apps.get_model("auth.Group", require_ready=False)
        emailaddress_model = django_apps.get_model("account.EmailAddress", require_ready=False)
        emailconfirmation_model = django_apps.get_model("account.EmailConfirmation", require_ready=False)

        user_model._meta.get_field('email')._unique = True

        @pghistory.track(
            pghistory.Snapshot('group.snapshot'),
            model_name='GroupsHistory',
            related_name='history',
            app_label='users',
        )
        class GroupProxy(group_model):
            class Meta:
                proxy = True

        @pghistory.track(  # Track events to permission group relationships
            pghistory.AfterInsert('permission.add'),
            pghistory.BeforeDelete('permission.remove'),
            model_name='GroupPermissionsHistory',
            obj_fk=None,
            related_name='history',
            app_label='users',
        )
        class GroupPermissionProxy(group_model.permissions.through):
            class Meta:
                proxy = True

        @pghistory.track(  # Track events to user group relationships
            pghistory.AfterInsert('group.add'),
            pghistory.BeforeDelete('group.remove'),
            model_name='UserGroupsHistory',
            obj_fk=None,
            related_name='history',
            app_label='users',
        )
        class UserGroupProxy(user_model.groups.through):
            class Meta:
                proxy = True

        @pghistory.track(  # Track events to user group relationships
            pghistory.AfterInsert('user_permission.add'),
            pghistory.BeforeDelete('user_permission.remove'),
            model_name='UserPermissionsHistory',
            obj_fk=None,
            related_name='history',
            app_label='users',
        )
        class UserPermissionProxy(user_model.user_permissions.through):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('emailaddress.snapshot'),
            model_name='EmailAddressHistory',
            related_name='history',
            app_label='users',
        )
        class EmailAddressProxy(emailaddress_model):
            class Meta:
                proxy = True

        @pghistory.track(
            pghistory.Snapshot('emailconfirmation.snapshot'),
            model_name='EmailConfirmationHistory',
            related_name='history',
            app_label='users',
        )
        class EmailConfirmationProxy(emailconfirmation_model):
            class Meta:
                proxy = True

        try:
            import attendees.users.signals  # noqa F401
        except ImportError:
            pass
