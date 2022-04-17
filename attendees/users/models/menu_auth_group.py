import pghistory
import model_utils.fields
import django.utils.timezone
from django.contrib.auth.models import Group
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.users.models import Menu


class MenuAuthGroup(TimeStampedModel, SoftDeletableModel):

    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )

    auth_group = models.ForeignKey(
        Group,
        null=False,
        blank=False,
        default=0,
        on_delete=models.SET(0),
    )

    read = models.BooleanField(
        null=False,
        blank=False,
        default=True,
    )

    write = models.BooleanField(
        null=False,
        blank=False,
        default=True,
    )

    menu = models.ForeignKey(
        Menu,
        null=False,
        blank=False,
        default=0,
        on_delete=models.SET(0),
    )

    class Meta:
        db_table = "users_menu_auth_groups"
        constraints = [
            models.UniqueConstraint(
                fields=["auth_group", "menu"],
                condition=models.Q(is_removed=False),
                name="auth_group_menu",
            )
        ]


class MenuAuthGroupsHistory(pghistory.get_event_model(
    MenuAuthGroup,
    pghistory.Snapshot('menuauthgroup.snapshot'),
    name='MenuAuthGroupsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='users.menuauthgroup')
    id = models.IntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    read = models.BooleanField(default=True)
    write = models.BooleanField(default=True)
    auth_group = models.ForeignKey(db_constraint=False, default=0, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='auth.group')
    menu = models.ForeignKey(db_constraint=False, default=0, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='users.menu')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'users_menu_auth_groupshistory'
