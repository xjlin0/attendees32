import pghistory
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
import django.utils.timezone
from model_utils.models import SoftDeletableModel, TimeStampedModel
import model_utils.fields
from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility


class Suite(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="suite",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    display_name = models.CharField(
        max_length=50, blank=False, null=False, db_index=True
    )
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    property = models.ForeignKey("Property", null=True, on_delete=models.SET_NULL)
    site = models.CharField(max_length=50, blank=True, help_text="2F floor, etc")

    class Meta:
        db_table = "whereabouts_suites"

    def get_absolute_url(self):
        return reverse("suite_detail", args=[str(self.id)])

    def __str__(self):
        return "%s %s %s" % (
            self.property.display_name,
            self.display_name,
            self.site or "",
        )


class SuitesHistory(pghistory.get_event_model(
    Suite,
    pghistory.Snapshot('suite.snapshot'),
    name='SuitesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.suite')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    site = models.CharField(blank=True, help_text='2F floor, etc', max_length=50)
    id = models.BigIntegerField()
    property = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.property')
    slug = models.SlugField(db_index=False)
    display_name = models.CharField(max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_suiteshistory'
