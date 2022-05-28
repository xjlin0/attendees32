import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
import model_utils.fields
from django.urls import reverse
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility


class Assembly(TimeStampedModel, SoftDeletableModel, Utility):
    places = GenericRelation("whereabouts.Place")
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    start = models.DateTimeField(null=True, blank=True, help_text="optional")
    finish = models.DateTimeField(null=True, blank=True, help_text="optional")
    category = models.ForeignKey(
        "persons.Category",
        null=False,
        blank=False,
        default=33,  # public
        on_delete=models.deletion.DO_NOTHING,
        help_text="normal, no-display, etc",
    )
    display_name = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="Uniq within Organization, adding year helps",
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    slug = models.SlugField(
        max_length=50,
        blank=False,
        null=False,
        unique=True,
        help_text="format: Organization_name-Assembly_name",
    )
    division = models.ForeignKey(
        "whereabouts.Division", null=False, blank=False, on_delete=models.SET(0)
    )
    infos = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text='example: {"need_age": 18}, please keep {} here even there\'s no data',
    )

    def get_absolute_url(self):
        return reverse("assembly_detail", args=[str(self.id)])

    class Meta:
        db_table = "occasions_assemblies"
        verbose_name_plural = "Assemblies"
        ordering = (
            "division",
            "display_order",
        )
        indexes = [
            GinIndex(
                fields=["infos"],
                name="assembly_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s" % self.display_name

    def get_addresses(self):
        return "\n".join([a.street for a in self.places.all() if a is not None])


# Todo 20210718 add uniq at save:  within organization, the display_name should be uniq for grouped dropdown

class AssembliesHistory(pghistory.get_event_model(
    Assembly,
    pghistory.Snapshot('assembly.snapshot'),
    name='AssembliesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.assembly')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    division = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.division')
    display_order = models.SmallIntegerField(default=0)
    infos = models.JSONField(blank=True, default=dict, help_text='example: {"need_age": 18}, please keep {} here even there\'s no data', null=True)
    slug = models.SlugField(db_index=False, help_text='format: Organization_name-Assembly_name')
    category = models.ForeignKey(db_constraint=False, default=33, help_text='normal, no-display, etc', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.category')
    display_name = models.CharField(help_text='Uniq within Organization, adding year helps', max_length=50)
    start = models.DateTimeField(blank=True, help_text='optional', null=True)
    finish = models.DateTimeField(blank=True, help_text='optional', null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_assemblieshistory'
