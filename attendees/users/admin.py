from django.contrib import admin, messages
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from django.db import models
from django.forms import TextInput
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget
from mptt.admin import MPTTModelAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from attendees.persons.models import PgHistoryPage
from attendees.users.forms import UserChangeForm, UserCreationForm

from .models import Menu, MenuAuthGroup
import os
import subprocess
from datetime import datetime
from django.urls import path
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse

User = get_user_model()

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(PgHistoryPage, GroupAdmin):
    pass  # to make original model admin shows PgHistoryPage

# from allauth.account.admin import EmailAddressAdmin
# from allauth.account.models import EmailAddress
# admin.site.unregister(EmailAddress)
# @admin.register(EmailAddress)   # Somehow Admin UI shows no history
# class EmailAddressAdmin(PgHistoryPage, EmailAddressAdmin):
#     pass  # to make original model admin shows PgHistoryPage


@admin.register(User)
class UserAdmin(PgHistoryPage, auth_admin.UserAdmin):
    change_list_template = "admin/user_change_list.html"
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

    list_display = ["username", "organization", "is_staff", "is_superuser"]
    search_fields = ["username"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('download-sql/', self.admin_site.admin_view(self.download_sql_backup), name='download_sql_backup'),
        ]
        return custom_urls + urls

    def download_sql_backup(self, request):
        if not request.user.is_superuser:
            return HttpResponse("Unauthorized", status=401)

        if request.method != "POST":
            return HttpResponse("Invalid request method", status=405)

        # Verify password from JS prompt
        pwd = request.POST.get('pwd', '')
        if not request.user.check_password(pwd):
            messages.error(request, "Incorrect admin password. Backup cancelled.")
            from django.shortcuts import redirect
            return redirect(request.META.get('HTTP_REFERER', '..'))

        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz"
        db_config = settings.DATABASES['default']
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_config['PASSWORD']
        
        # 移除 -F c 讓 pg_dump 產出預設的 Plain-text SQL
        pg_cmd = [
            'pg_dump',
            '-h', db_config['HOST'],
            '-p', str(db_config['PORT']),
            '-U', db_config['USER'],
            db_config['NAME']
        ]

        try:
            # 第一段：執行 pg_dump
            pg_process = subprocess.Popen(pg_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 第二段：將 pg_dump 的輸出導向給 gzip 進行即時壓縮
            gzip_process = subprocess.Popen(['gzip', '-c'], stdin=pg_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 關閉 pg_process 在主程序的 stdout，讓它完全交給 gzip，避免 deadlock
            pg_process.stdout.close()

            def file_iterator(proc):
                while True:
                    chunk = proc.stdout.read(8192)
                    if not chunk:
                        break
                    yield chunk
                proc.stdout.close()
                proc.wait()
                if proc.returncode != 0:
                    stderr_output = proc.stderr.read().decode('utf-8')
                    print(f"gzip error: {stderr_output}")

            # content_type 改為 gzip
            response = StreamingHttpResponse(file_iterator(gzip_process), content_type='application/gzip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            return HttpResponse(f"Backup failed to start: {str(e)}", status=500)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        if request.user.is_superuser:
            return self.superuser_fieldsets
        else:
            return self.general_fieldsets

    def save_model(self, request, obj, form, change):
        if not obj.organization:
            obj.organization_id = request.user and request.user.organization_id or 0
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            if request.resolver_match.func.__name__ == "changelist_view":
                messages.info(
                    request,
                    "You are seeing all records across organizations as a superuser.",
                )
            return qs
        else:
            if request.resolver_match.func.__name__ == "changelist_view":
                messages.warning(
                    request,
                    "Not all, but only those records accessible to you will be listed here.",
                )
            return qs.filter(organization=request.user.organization)


class MenuAuthGroupInline(PgHistoryPage, admin.TabularInline):
    model = MenuAuthGroup
    extra = 0


@admin.register(Menu)
class MenuAdmin(PgHistoryPage, MPTTModelAdmin):
    search_fields = ["urn", "url_name", "display_name"]
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
        if request.user.is_superuser:
            if request.resolver_match.func.__name__ == "changelist_view":
                messages.info(
                    request,
                    "You are seeing all records across organizations as a superuser.",
                )
            return qs
        else:
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
