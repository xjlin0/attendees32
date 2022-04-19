from django.contrib import admin, messages
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget

# from attendees.occasions.models import *
# from attendees.persons.models import *
#
# from .models import *
from attendees.persons.models import PgHistoryPage
from attendees.whereabouts.models import Place, Campus, Property, Suite, Room, Division, Organization


class PlaceAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("id", "display_name", "infos")
    list_display_links = ("id",)
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "display_name", "subject", "address")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(organization=request.user.organization)


class DivisionAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    list_display_links = ("display_name",)
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "organization", "display_name", "slug", "infos")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            if request.resolver_match.func.__name__ == "changelist_view":
                messages.warning(
                    request,
                    "Not all, but only those records accessible to you will be listed here.",
                )
            return qs.filter(organization=request.user.organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization":
            kwargs["queryset"] = Organization.objects.all() if request.user.is_superuser else Organization.objects.filter(pk=request.user.organization_pk())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PropertyAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "display_name", "slug", "campus", "modified")


class CampusAdmin(PgHistoryPage, admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display = ("display_name", "organization", "slug", "modified")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(organization=request.user.organization)


class SuiteAdmin(PgHistoryPage, admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "display_name", "slug", "site", "modified")


class RoomAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display = ("display_name", "label", "suite", "infos", "modified")


class OrganizationAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display = ("display_name", "slug", "infos", "modified")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            if request.resolver_match.func.__name__ == "changelist_view":
                messages.warning(
                    request,
                    "Not all, but only those records accessible to you will be listed here.",
                )
            return qs.filter(pk=request.user.organization_pk())


admin.site.register(Place, PlaceAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Property, PropertyAdmin)
admin.site.register(Suite, SuiteAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Division, DivisionAdmin)
admin.site.register(Organization, OrganizationAdmin)
