from django.contrib import admin, messages
from django.db import models
from django.db.models import Q
from django_json_widget.widgets import JSONEditorWidget

from attendees.occasions.models import Attendance, Meet, Team, Character, Assembly
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
from attendees.whereabouts.models import Division


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
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
    list_filter = ("type",)
    readonly_fields = ["id", "created", "modified"]
    list_display_links = ("display_name",)
    list_display = ("id", "type", "display_name", "display_order", "infos")

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class PastAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
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
        models.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("id", "display_name", "infos")
    readonly_fields = ["is_removed", "id", "created", "modified"]
    inlines = (FolkAttendeeInline,)
    list_display_links = ("id",)
    list_display = ("id", "display_name", "is_removed", "infos", "division", "category")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    tuple(["display_name", "display_order", "division"]),
                    tuple(["infos"]),
                    tuple(["category"]),
                    tuple(["id"]),
                    tuple(["created"]),
                    tuple(["modified"]),
                    tuple(["is_removed"]),
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


class FolkAttendeeAdmin(PgHistoryPage, admin.ModelAdmin):
    readonly_fields = ["display_folk_id", "is_removed", "id", "created", "modified"]
    list_display = ("id", "folk", "attendee", "role", "is_removed", "infos")
    search_fields = ("id", "attendee__id", "attendee__infos", "folk__id", "infos")

    def display_folk_id(self, obj):
        return obj.folk.id

    display_folk_id.short_description = 'Folk id'

    def get_queryset(self, request):
        message = "Not all, but only those records accessible to you will be listed here."
        if request.user.is_superuser:
            qs = FolkAttendee.all_objects.all()
        else:
            qs = super().get_queryset(request)

        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                message + (" Including removed ones." if request.user.is_superuser else ""),
            )
        ordering = super().get_ordering(request)
        return qs.filter(folk__division__organization=request.user.organization).order_by(*ordering)


class RelationAdmin(PgHistoryPage, admin.ModelAdmin):
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
        models.JSONField: {"widget": JSONEditorWidget},
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "division":
            kwargs["queryset"] = Division.objects.filter(organization=request.user.organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RegistrationAdmin(PgHistoryPage, admin.ModelAdmin):
    search_fields = (
        'registrant__first_name',
        'registrant__last_name',
        'registrant__first_name2',
        'registrant__last_name2',
    )
    autocomplete_fields = ('registrant',)
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
    list_display_links = ("registrant",)
    list_display = ("id", "registrant", "assembly", "infos", "modified")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(assembly__division__organization=request.user.organization)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assembly":
            kwargs["queryset"] = Assembly.objects.filter(division__organization=request.user.organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class AttendanceInline(admin.StackedInline):
    model = Attendance
    extra = 0


class AttendingAdmin(PgHistoryPage, admin.ModelAdmin):
    # list_per_page = 1000
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = (
        "id",
        "attendee__first_name",
        "attendee__last_name",
        "attendee__first_name2",
        "attendee__last_name2",
    )
    list_display_links = ("attendee",)
    autocomplete_fields = ('attendee', 'registration')
    list_filter = ("meets",)
    readonly_fields = ["id", "created", "modified"]
    inlines = (
        AttendingMeetInline,
    )  # add AttendanceInline when creating new Attending will fails on meet_names
    list_display = ("id", "registration", "attendee", "meet_names")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(attendee__division__organization=request.user.organization)

    class Media:
        css = {"all": ("css/admin.css",)}
        js = ["js/admin/list_filter_collapse.js"]


class NoteAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
    search_fields = ("body",)
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


class AttendingMeetAdmin(PgHistoryPage, admin.ModelAdmin):
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
    list_display_links = ("attending",)
    autocomplete_fields = ('attending',)
    search_fields = ('infos', 'attending__attendee__infos',)
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

    # def get_form(self, request, obj=None, **kwargs):
    #     self.instance = obj
    #     return super(AttendingMeetAdmin, self).get_form(request, obj=obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # print("hi Todo 20220528 change character/team here based on meet here is self.instance", self.instance)
        if db_field.name == "meet":
            kwargs["queryset"] = Meet.objects.filter(assembly__division__organization=request.user.organization)
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.filter(type='attendance')
        if db_field.name == "team":
            kwargs["queryset"] = Team.objects.filter(meet__assembly__division__organization=request.user.organization)
        if db_field.name == "character":
            kwargs["queryset"] = Character.objects.filter(assembly__division__organization=request.user.organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match.func.__name__ == "changelist_view":
            messages.warning(
                request,
                "Not all, but only those records accessible to you will be listed here.",
            )
        return qs.filter(attending__attendee__division__organization=request.user.organization)


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
