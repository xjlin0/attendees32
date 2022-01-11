
from django.contrib import admin
from django.contrib.postgres import fields

from django_json_widget.widgets import JSONEditorWidget
from attendees.occasions.models import Attendance, MessageTemplate, Assembly, Price, Character, Meet, Gathering, Team


# Register your models here.


# class AssemblyContactAdmin(admin.ModelAdmin):
#     readonly_fields = ['id', 'created', 'modified']
#     list_display = ('assembly', 'contact', 'modified')


# class AssemblyContactInline(admin.TabularInline):
#     model = AssemblyContact
#     extra = 0


class MessageTemplateAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    readonly_fields = ["id", "created", "modified"]
    list_display = ("truncate_template", "type", "modified")

    def truncate_template(self, obj):
        return list(obj.templates.values())[0][:100] + "..."


class AssemblyAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    # inlines = (AssemblyContactInline,)
    list_display_links = ("display_name",)
    list_display = ("id", "division", "display_name", "slug", "get_addresses")
    readonly_fields = ["id", "created", "modified"]


class PriceAdmin(admin.ModelAdmin):
    list_display = ("display_name", "price_type", "start", "price_value", "modified")


class AttendanceAdmin(admin.ModelAdmin):
    list_display_links = ("get_attendee",)
    list_filter = (
        ("gathering", admin.RelatedOnlyFieldListFilter),
        ("character", admin.RelatedOnlyFieldListFilter),
        ("team", admin.RelatedOnlyFieldListFilter),
    )  # too many attendings even with ('attending', admin.RelatedOnlyFieldListFilter)
    list_display = (
        "id",
        "attendance_info",
        "get_attendee",
        "character",
        "team",
        "infos",
    )
    readonly_fields = ["id", "created", "modified"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["start", "finish"]),
                    tuple(["gathering", "team"]),
                    tuple(["attending", "character"]),
                    tuple(["free", "display_order", "category"]),
                    tuple(["id", "created", "modified"]),
                    tuple(["infos"]),
                ),
            },
        ),
    )

    def get_attendee(self, obj):
        return obj.attending.attendee

    get_attendee.admin_order_field = "attendee"  # Allows column order sorting
    get_attendee.short_description = "attendee"  # Rename

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class AttendanceInline(admin.StackedInline):
    model = Attendance
    extra = 0
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["start", "finish", "free", "category"]),
                    tuple(["gathering", "team", "attending", "character"]),
                    tuple(["infos"]),
                ),
            },
        ),
    )
    #
    # def get_queryset(self, request):
    #     qs = super(AttendanceInline, self).get_queryset(request)
    #     return qs[:10]  # does not work


class CharacterAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    list_filter = ("assembly", "type")
    readonly_fields = ["id", "created", "modified"]
    list_display_links = ("display_name",)
    list_display = ("id", "assembly", "display_name", "slug", "display_order", "type")

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class TeamAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("display_name",)}
    readonly_fields = ["id", "created", "modified"]
    list_display_links = ("display_name",)
    list_display = ("id", "display_name", "slug", "meet", "display_order", "modified")


class MeetAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    prepopulated_fields = {"slug": ("display_name",)}
    search_fields = ("display_name",)
    list_filter = ("assembly",)
    list_display_links = ("display_name",)
    list_display = ("id", "display_name", "slug", "assembly", "site")
    readonly_fields = ["id", "created", "modified"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["start", "finish", "slug"]),
                    tuple(
                        [
                            "display_name",
                            "major_character",
                            "infos",
                            "shown_audience",
                            "audience_editable",
                        ]
                    ),
                    tuple(["site_type", "assembly", "site_id"]),
                    tuple(["id", "created", "modified"]),
                ),
                # 'classes': ['hijack', ],  # the above entire fieldset
            },
        ),
    )

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class GatheringAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    # inlines = (AttendanceInline,)  # too many and haven't found easy way to limit inline models
    list_display_links = ("display_name",)
    search_fields = ("meet__display_name", "display_name")
    list_filter = ("meet",)
    list_display = ("id", "meet", "start", "display_name", "site", "infos")
    readonly_fields = ["id", "created", "modified"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["start", "finish"]),
                    tuple(["display_name", "infos"]),
                    tuple(["site_type", "meet", "site_id", "occurrence"]),
                    tuple(["id", "created", "modified"]),
                ),
            },
        ),
    )

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


admin.site.register(MessageTemplate, MessageTemplateAdmin)
admin.site.register(Assembly, AssemblyAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(Character, CharacterAdmin)
admin.site.register(Meet, MeetAdmin)
admin.site.register(Gathering, GatheringAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Attendance, AttendanceAdmin)
