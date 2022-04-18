from django.contrib import admin, messages
from django.contrib.postgres import fields
from django.db.models import Q
from django_json_widget.widgets import JSONEditorWidget
from django_summernote.admin import SummernoteModelAdmin

from attendees.occasions.models import Attendance
from attendees.persons.models import AttendingMeet, FolkAttendee, Category, Past, Note, Folk, Attendee, Registration, \
    Attending, Relation, PgHistoryPage


# from attendees.occasions.models import *
# from attendees.whereabouts.models import *
#
# from .models import *

# Register your models here.


# class AttendeeContactInline(admin.StackedInline):
#     model = Locate
#     extra = 0


class AttendingMeetInline(admin.StackedInline):
    model = AttendingMeet
    extra = 0


# class RelationshipInline(admin.TabularInline):
#     model = Relationship
#     fk_name = 'from_attendee'
#     extra = 0


class FolkAttendeeInline(admin.TabularInline):
    model = FolkAttendee
    extra = 0


class CategoryAdmin(PgHistoryPage, admin.ModelAdmin):
    readonly_fields = ["id", "created", "modified"]
    list_display_links = ("display_name",)
    list_display = ("id", "type", "display_name", "display_order", "infos")


class PastAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    # Todo 20210528  combine with NoteAdmin's show_secret
    search_fields = ("id", "display_name", "infos")
    readonly_fields = ["id", "created", "modified"]
    list_display = ("subject", "category", "display_order", "display_name", "when")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        counseling_category = Category.objects.filter(
            type="note", display_name=Past.COUNSELING
        ).first()

        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        requester_permission = {
            "infos__show_secret__" + request.user.attendee_uuid_str(): True
        }

        if request.user.is_counselor():
            counselors_permission = {"infos__show_secret__" + Past.ALL_COUNSELORS: True}
            return qs.filter(
                Q(organization=request.user.organization),
                (
                    ~Q(category=counseling_category)
                    | (
                        Q(category=counseling_category)
                        and (Q(**requester_permission) | Q(**counselors_permission))
                    )
                ),
            )

        else:
            return qs.filter(
                Q(organization=request.user.organization),
                (
                    Q(**requester_permission)
                    | Q(infos__show_secret={})
                    | Q(infos__show_secret__isnull=True)
                ),
            ).exclude(category__display_name=Past.COUNSELING)


class FolkAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("id", "display_name", "infos")
    readonly_fields = ["id", "created", "modified"]
    inlines = (FolkAttendeeInline,)
    list_display_links = ("id",)
    list_display = ("id", "display_name", "infos", "division", "category")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["display_name", "display_order", "division"]),
                    tuple(["infos"]),
                    tuple(["category", "id", "created", "modified"]),
                ),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(division__organization=request.user.organization)


class FolkAttendeeAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "folk", "attendee", "role", "infos")


class RelationAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "created", "modified"]
    list_display_links = ("title",)
    list_display = (
        "id",
        "title",
        "reciprocal_ids",
        "emergency_contact",
        "scheduler",
        "relative",
        "display_order",
    )


class AttendeeAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("id", "infos")
    readonly_fields = ["id", "created", "modified"]
    # inlines = (RelationshipInline,)  # AttendeeContactInline
    list_display_links = ("id",)
    list_display = ("id", "full_name", "infos")

    def full_name(self, obj):
        return obj.infos.get("names", {}).get("original")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(division__organization=request.user.organization)


class RegistrationAdmin(PgHistoryPage, admin.ModelAdmin):
    # list_per_page = 1000
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    list_display_links = ("registrant",)
    list_display = ("id", "registrant", "assembly", "infos", "modified")


class AttendanceInline(admin.StackedInline):
    model = Attendance
    extra = 0


class AttendingAdmin(admin.ModelAdmin):
    # list_per_page = 1000
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = (
        "attendee__first_name",
        "attendee__last_name",
        "attendee__first_name2",
        "attendee__last_name2",
    )
    list_display_links = ("attendee",)
    list_filter = ("meets",)
    readonly_fields = ["id", "created", "modified"]
    inlines = (
        AttendingMeetInline,
    )  # add AttendanceInline when creating new Attending will fails on meet_names
    list_display = ("id", "registration", "attendee", "meet_names")

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class NoteAdmin(PgHistoryPage, SummernoteModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("body",)
    readonly_fields = ["id", "created", "modified"]
    summernote_fields = ("body",)
    readonly_fields = ["id", "created", "modified"]
    list_display = ("id", "category", "content_object", "display_order", "modified")

    def get_queryset(self, request):  # even super user cannot see all in DjangoAdmin
        qs = super().get_queryset(request)
        counseling_category = Category.objects.filter(
            type="note", display_name=Note.COUNSELING
        ).first()

        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those notes accessible to you will be listed here.",
            )
        if request.user.is_counselor():
            requester_permission = {
                "infos__show_secret__" + request.user.attendee_uuid_str(): True
            }
            counselors_permission = {"infos__show_secret__" + Note.ALL_COUNSELORS: True}
            return qs.filter(
                Q(organization=request.user.organization),
                (
                    ~Q(category=counseling_category)
                    | (
                        Q(category=counseling_category)
                        and (Q(**requester_permission) | Q(**counselors_permission))
                    )
                ),
            )
        return qs.filter(organization=request.user.organization).exclude(
            category=counseling_category
        )


# class RelationshipAdmin(admin.ModelAdmin):
#     formfield_overrides = {
#         fields.JSONField: {'widget': JSONEditorWidget},
#     }
#     search_fields = ('id', 'infos', 'from_attendee__id', 'to_attendee__id')
#     list_display_links = ('relation',)
#     readonly_fields = ['id', 'created', 'modified']
#     list_display = ('id', 'from_attendee', 'relation', 'to_attendee', 'emergency_contact', 'scheduler', 'in_family', 'finish')
#
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if request.resolver_match.func.__name__ == 'changelist_view':
#             messages.warning(request, 'Not all, but only those records accessible to you will be listed here.')
#         requester_permission = {'infos__show_secret__' + request.user.attendee_uuid_str(): True}
#         return qs.filter(
#             (Q(from_attendee__division__organization=request.user.organization)
#              |
#              Q(to_attendee__division__organization=request.user.organization) ),
#             (Q(**requester_permission)
#              |
#              Q(infos__show_secret={}) ),
#         )


class AttendingMeetAdmin(admin.ModelAdmin):
    list_display_links = ("attending",)
    readonly_fields = ["id", "created", "modified"]
    list_display = (
        "id",
        "attending",
        "meet",
        "character",
        "category",
        "finish",
        "modified",
    )


admin.site.register(Category, CategoryAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(Past, PastAdmin)
admin.site.register(Folk, FolkAdmin)
admin.site.register(Attendee, AttendeeAdmin)
admin.site.register(FolkAttendee, FolkAttendeeAdmin)
admin.site.register(Registration, RegistrationAdmin)
admin.site.register(Attending, AttendingAdmin)
admin.site.register(Relation, RelationAdmin)
# admin.site.register(Relationship, RelationshipAdmin)
admin.site.register(AttendingMeet, AttendingMeetAdmin)
