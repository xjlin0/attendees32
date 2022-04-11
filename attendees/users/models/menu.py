import pghistory
import model_utils.fields
import mptt.fields
import django.utils.timezone
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


class MenusHistory(pghistory.get_event_model(
    Menu,
    pghistory.Snapshot('menu.snapshot'),
    name='MenusHistory',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='users.menu')
    id = models.IntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    organization = models.ForeignKey(db_constraint=False, default=0, help_text='Organization of the menu', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')
    is_removed = models.BooleanField(default=False)
    tree_id = models.PositiveIntegerField(editable=False)
    level = models.PositiveIntegerField(editable=False)
    lft = models.PositiveIntegerField(editable=False)
    rght = models.PositiveIntegerField(editable=False)
    display_order = models.SmallIntegerField(default=0)
    category = models.CharField(default='main', help_text="Type of menu, such as 'main', 'side', etc", max_length=32)
    url_name = models.SlugField(db_index=False, help_text="view name of the path, such as 'assembly_attendances', 'divider between index and register links', etc. For API it's class name", max_length=255)
    display_name = models.CharField(help_text="description of the path, such as 'Character index page', 'divider between index and register links', etc", max_length=50)
    infos = models.JSONField(blank=True, default=dict, help_text="HTML attributes & more such as {'class': 'dropdown-item'}. Please keep {} here even no data.", null=True)
    parent = mptt.fields.TreeForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='users.menu')
    urn = models.CharField(blank=True, help_text="use relative path (including leading & ending slash '/') such as /app/division/assembly/page-name", max_length=255, null=True)
    html_type = models.CharField(blank=True, help_text='HTML tags such as div or a. For API it can be blank', max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = "users_menushistory"
