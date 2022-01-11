from django.contrib import admin, messages
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget
from attendees.occasions.models import *
from attendees.persons.models import *
from .models import *


class PlaceAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    search_fields = ('id', 'display_name', 'infos')
    list_display_links = ('id',)
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('id', 'display_name', 'subject', 'address')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == 'changelist_view':
            messages.warning(request, 'Not all, but only those records accessible to you will be listed here.')
        return qs.filter(organization=request.user.organization)


class DivisionAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    list_display_links = ('display_name',)
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('id', 'organization', 'display_name', 'slug', 'modified')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == 'changelist_view':
            messages.warning(request, 'Not all, but only those records accessible to you will be listed here.')
        return qs.filter(organization=request.user.organization)


class PropertyAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('id', 'display_name', 'slug', 'campus', 'modified')


class CampusAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('display_name', 'organization', 'slug', 'modified')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == 'changelist_view':
            messages.warning(request, 'Not all, but only those records accessible to you will be listed here.')
        return qs.filter(organization=request.user.organization)


class SuiteAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('id', 'display_name', 'slug',  'site', 'modified')


class RoomAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('display_name', 'label', 'suite', 'accessibility', 'modified')


class OrganizationAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ['id', 'created', 'modified']
    list_display = ('display_name', 'slug', 'infos', 'modified')


admin.site.register(Place, PlaceAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Property, PropertyAdmin)
admin.site.register(Suite, SuiteAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Division, DivisionAdmin)
admin.site.register(Organization, OrganizationAdmin)
