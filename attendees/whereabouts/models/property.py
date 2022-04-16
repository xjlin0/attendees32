import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
from django.urls import reverse
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility


class Property(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    places = GenericRelation("whereabouts.Place")
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="property",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    display_name = models.CharField(
        max_length=50, blank=False, null=False, db_index=True
    )
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    campus = models.ForeignKey("Campus", null=True, on_delete=models.SET_NULL)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"2010id": "3"}. Please keep {} here even no data',
    )

    class Meta:
        db_table = "whereabouts_properties"
        verbose_name_plural = "Properties"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="property_infos_gin",
            ),
        ]

    def get_absolute_url(self):
        return reverse("property_detail", args=[str(self.id)])

    def __str__(self):
        return "%s %s %s" % (
            self.campus,
            self.display_name,
            self.places.all()
            and "; ".join([a.street for a in self.places.all()])
            or "",
        )


class PropertiesHistory(pghistory.get_event_model(
    Property,
    pghistory.Snapshot('property.snapshot'),
    name='PropertiesHistory',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.property')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    id = models.IntegerField()
    campus = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.campus')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"2010id": "3"}. Please keep {} here even no data', null=True)
    slug = models.SlugField(db_index=False)
    display_name = models.CharField(max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_propertieshistory'
