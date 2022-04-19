import pghistory
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility

from . import Organization


class Division(TimeStampedModel, SoftDeletableModel, Utility):
    link_notes = GenericRelation(Note)
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="division",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    organization = models.ForeignKey(
        Organization, null=False, blank=False, on_delete=models.SET(0)
    )
    display_name = models.CharField(max_length=50, blank=False, null=False, help_text='"Junior Ministry" is a magic word to show certain Attendee infos in attendee_update_view.js')
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    audience_auth_group = models.ForeignKey(
        "auth.Group",
        null=False,
        blank=False,
        help_text="which auth group does the joining general participant belong to?",
        on_delete=models.SET(0),
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"show_attendee_infos": {"insurer": true}}. Please keep {} here even no data',
    )
    #  Todo 20210529: rename division of "data" to "organizational"

    class Meta:
        db_table = "whereabouts_divisions"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="division_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s" % self.display_name


class DivisionsHistory(pghistory.get_event_model(
    Division,
    pghistory.Snapshot('division.snapshot'),
    name='DivisionsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.division')
    pgh_label = models.TextField(help_text='The event label.')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    organization = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')
    is_removed = models.BooleanField(default=False)
    audience_auth_group = models.ForeignKey(db_constraint=False, help_text='which auth group does the joining general participant belong to?', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='auth.group')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"show_attendee_infos": {"insurer": true}}. Please keep {} here even no data', null=True)
    slug = models.SlugField(db_index=False)
    display_name = models.CharField(help_text='"Junior Ministry" is a magic word to show certain Attendee infos in attendee_update_view.js', max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_divisionshistory'
