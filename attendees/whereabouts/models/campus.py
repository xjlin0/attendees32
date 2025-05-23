import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.urls import reverse
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel
from schedule.models import CalendarRelation

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility
from attendees.whereabouts.models import Organization


class Campus(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    calendar_relations = GenericRelation(CalendarRelation)
    places = GenericRelation("whereabouts.Place")
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="campus",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    organization = models.ForeignKey(
        Organization,
        verbose_name="used by",
        null=False,
        blank=False,
        on_delete=models.SET(0),
        help_text="which organization use this?",
    )
    display_name = models.CharField(
        max_length=50, blank=False, null=False, db_index=True
    )
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"hostname": "where the app deployed"}. Please keep {} here even no data',
    )

    class Meta:
        db_table = "whereabouts_campuses"
        verbose_name_plural = "Campuses"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="campus_infos_gin",
            ),
        ]

    def get_absolute_url(self):
        return reverse("campus_detail", args=[str(self.id)])

    def __str__(self):
        return "%s" % self.display_name


class CampusesHistory(pghistory.get_event_model(
    Campus,
    pghistory.Snapshot('campus.snapshot'),
    pghistory.BeforeDelete('campus.before_delete'),
    name='CampusesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.campus')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    organization = models.ForeignKey(db_constraint=False, help_text='which organization use this?', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization', verbose_name='used by')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"hostname": "where the app deployed"}. Please keep {} here even no data', null=True)
    slug = models.SlugField(db_index=False)
    display_name = models.CharField(max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_campuseshistory'
