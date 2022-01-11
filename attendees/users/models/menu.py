from django.contrib.auth.models import Group
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey

from attendees.whereabouts.models import Organization


class Menu(MPTTModel, TimeStampedModel, SoftDeletableModel):
    """
    Todo: Raise ValueError if the instance.get_level() > 1 due to Boostrap 4 dropdown-submenu limit,
    or smartmenus will be needed.

    UniqueConstraint(fields=['organization', 'category', 'html_type', 'url_name'], condition=models.Q(is_removed=False))
    cannot be used since some menu repatitive for different user groups

    """

    ATTENDEE_CREATE_VIEW = "attendee_create_view"
    ATTENDEE_UPDATE_VIEW = "attendee_update_view"
    ATTENDEE_UPDATE_SELF = "attendee_update_self"

    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )

    organization = models.ForeignKey(
        Organization,
        null=False,
        blank=False,
        default=0,
        on_delete=models.SET(0),
        help_text="Organization of the menu",
    )

    category = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        db_index=True,
        default="main",
        help_text="Type of menu, such as 'main', 'side', etc",
    )

    parent = TreeForeignKey(
        "self", on_delete=models.SET(-1), null=True, blank=True, related_name="children"
    )

    html_type = models.CharField(
        max_length=50,
        blank=True,
        null=False,
        help_text="HTML tags such as div or a. For API it can be blank",
    )

    urn = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="use relative path (including leading & ending slash '/') such as /app/division/assembly/page-name",
    )

    url_name = models.SlugField(
        max_length=255,
        blank=False,
        null=False,
        db_index=True,
        help_text="view name of the path, such as 'assembly_attendances', 'divider between index and register links', "
        "etc. For API it's class name",
    )

    display_name = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="description of the path, such as 'Character index page', 'divider between index and register "
        "links', etc",
    )

    display_order = models.SmallIntegerField(default=0, blank=False, null=False)

    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text="HTML attributes & more such as {'class': 'dropdown-item'}. Please keep {} here even no data.",
    )

    auth_groups = models.ManyToManyField(
        Group, through="MenuAuthGroup", related_name="auth_groups"
    )

    class MPTTMeta:
        order_insertion_by = ["display_order", "display_name"]

    class Meta:
        db_table = "users_menus"

    def __str__(self):
        return "%s %s %s URN: ...%s" % (
            self.organization_slug,
            self.category.upper(),
            self.display_name,
            self.urn[-40:] if self.urn else "",
        )

    @property
    def organization_slug(self):
        return self.organization.slug if self.organization else ""

    @staticmethod
    def user_can_create_attendee(user, url_name=ATTENDEE_CREATE_VIEW):
        return Menu.objects.filter(
            auth_groups__in=user.groups.all(),
            url_name=url_name,
            menuauthgroup__write=True,
            is_removed=False,
        ).exists()
