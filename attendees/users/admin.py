import pghistory
from django.contrib import admin, messages
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from django.db import models
from django.forms import TextInput
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget
from mptt.admin import MPTTModelAdmin

from attendees.persons.models import PgHistoryPage
from attendees.users.forms import UserChangeForm, UserCreationForm

from .models import Menu, MenuAuthGroup

User = get_user_model()


@admin.register(User)
class UserAdmin(PgHistoryPage, auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    superuser_fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "User",
            {
                "fields": (
                    "is_superuser",
                    "organization",
                )
            },
        ),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    general_fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    # add_fieldsets = auth_admin.UserAdmin.add_fieldsets

    list_display = ["username", "organization", "is_staff", "is_superuser"]
    search_fields = ["username"]

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        if request.user.is_superuser:
            return self.superuser_fieldsets
        else:
            return self.general_fieldsets

    # def get_fieldsets(self, request, obj=None):
    #     credentials = (None, {"fields": ("username", "password")})
    #     super_users = ("Super user fields", {"fields": ("organization", "is_superuser")})
    #     personal_info = (_("Personal info"), {"fields": ("name", "email")})
    #     permissions = (_("Permissions"), {"fields": ("is_active", "is_staff", "groups", "user_permissions")})
    #     important_dates = (_("Important dates"), {"fields": ("last_login", "date_joined")})
    #
    #     if request.user.is_superuser:
    #         return (credentials, super_users, personal_info, permissions, important_dates)
    #     else:
    #         return (credentials, personal_info, permissions, important_dates)

# from django.contrib import admin, messages
# from django.contrib.auth import admin as auth_admin
# from django.contrib.auth import get_user_model
# from django.contrib.postgres import fields
# from django.forms import TextInput
# from django.db import models
# from django_json_widget.widgets import JSONEditorWidget
# from mptt.admin import MPTTModelAdmin
# from .models import Menu, MenuAuthGroup
#
# from attendees.users.forms.admin_forms import UserChangeForm, UserCreationForm

# User = get_user_model()


# @admin.register(User)
# class UserAdmin(auth_admin.UserAdmin):
#
#     form = UserChangeForm
#     add_form = UserCreationForm
#     fieldsets = (
#                     ("User", {"fields": ("name", "organization",)}),
#                 ) + auth_admin.UserAdmin.fieldsets
#     list_display = ["username", "organization", "is_staff", "is_superuser"]
#     search_fields = ["name"]


class MenuAuthGroupInline(PgHistoryPage, admin.TabularInline):
    model = MenuAuthGroup
    extra = 0


@admin.register(Menu)
class MenuAdmin(PgHistoryPage, MPTTModelAdmin):
    readonly_fields = ["id", "created", "modified"]
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
        models.CharField: {"widget": TextInput(attrs={"size": "100%"})},
    }
    mptt_level_indent = 20
    prepopulated_fields = {"url_name": ("display_name",)}
    list_display = ("display_name", "is_removed", "category", "display_order", "urn")
    list_editable = ("is_removed", "display_order")
    inlines = (MenuAuthGroupInline,)
    list_display_links = ("display_name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(organization=request.user.organization)


@admin.register(MenuAuthGroup)
class MenuAuthGroupAdmin(PgHistoryPage, admin.ModelAdmin):

    list_display = (
        "auth_group",
        "read",
        "write",
        "menu",
    )
