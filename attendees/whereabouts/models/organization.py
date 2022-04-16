import pghistory
from django.contrib.contenttypes.fields import GenericRelation

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel
import model_utils.fields
import django.utils.timezone

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility


class Organization(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    places = GenericRelation("whereabouts.Place")
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="organization",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    slug = models.SlugField(
        max_length=50,
        blank=False,
        null=False,
        unique=True,
        help_text="alphanumeric only",
    )
    display_name = models.CharField(max_length=50, blank=False, null=False)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.organization_infos,
        help_text='Example: {"hostname": "where the app deployed"}. Please keep {} here even no data',
    )

    class Meta:
        db_table = "whereabouts_organizations"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="organization_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s" % self.display_name


class OrganizationsHistory(pghistory.get_event_model(
    Organization,
    pghistory.Snapshot('organization.snapshot'),
    name='OrganizationsHistory',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.organization')
    id = models.BigIntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    slug = models.SlugField(db_index=False, help_text='alphanumeric only')
    display_name = models.CharField(max_length=50)
    infos = models.JSONField(blank=True, default=Utility.organization_infos, help_text='Example: {"hostname": "where the app deployed"}. Please keep {} here even no data', null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_organizationshistory'
