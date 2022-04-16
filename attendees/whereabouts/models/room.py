import pghistory
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
from django.urls import reverse
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility


class Room(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="room",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    display_name = models.CharField(
        max_length=50, blank=False, null=False, db_index=True
    )
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    suite = models.ForeignKey("Suite", null=True, on_delete=models.SET_NULL)
    label = models.CharField(max_length=20, blank=True)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"accessibility": 3}. Please keep {} here even no data',
    )

    class Meta:
        db_table = "whereabouts_rooms"
        indexes = [GinIndex(fields=["infos"], name="room_infos_gin", ),]

    def get_absolute_url(self):
        return reverse("room_detail", args=[str(self.id)])

    def __str__(self):
        return "%s %s %s" % (
            self.suite.display_name,
            self.display_name,
            self.label or "",
        )


class RoomsHistory(pghistory.get_event_model(
    Room,
    pghistory.Snapshot('room.snapshot'),
    name='RoomsHistory',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='whereabouts.room')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    slug = models.SlugField(db_index=False)
    id = models.IntegerField()
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"accessibility": 3}. Please keep {} here even no data', null=True)
    suite = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.suite')
    display_name = models.CharField(max_length=50)
    label = models.CharField(blank=True, max_length=20)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'whereabouts_roomshistory'
