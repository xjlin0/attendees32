from uuid import uuid4
import pghistory
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
import django.utils.timezone
import model_utils.fields
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Utility


class Note(TimeStampedModel, SoftDeletableModel):
    COUNSELING = "counseling"  # for private data, and only assigned counselors
    ALL_COUNSELORS = (
        "all_counselors_"  # for private data, but accessible to all counselors
    )

    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, serialize=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET(0))
    object_id = models.CharField(max_length=36)
    content_object = GenericForeignKey("content_type", "object_id")
    category = models.ForeignKey(
        "persons.Category",
        null=False,
        blank=False,
        on_delete=models.SET(0),
        help_text="subtype: for note it's public/counseling sub-types etc",
    )
    organization = models.ForeignKey(
        "whereabouts.Organization", null=False, blank=False, on_delete=models.SET(0)
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    body = models.TextField()
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.relationship_infos,
        help_text='Example: {"owner": "John"}. Please keep {} here even no data',
    )

    def __str__(self):
        return "%s %s %s" % (self.content_type, self.content_object, self.category)

    class Meta:
        db_table = "persons_notes"
        ordering = (
            "organization",
            "category",
            "content_type",
            "object_id",
            "display_order",
            "-modified",
        )
        indexes = [
            models.Index(
                fields=["content_type", "object_id"],
                condition=models.Q(is_removed=False),
                name="note_content_objects",
            ),
            GinIndex(
                fields=["infos"],
                name="note_infos_gin",
            ),
        ]

    # @property
    # def iso_updated_at(self):
    #     return self.modified.isoformat()


class NotesHistory(pghistory.get_event_model(
    Note,
    pghistory.Snapshot('note.snapshot'),
    name='NotesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    id = models.UUIDField(db_index=True, default=uuid4, editable=False, serialize=False)
    object_id = models.CharField(max_length=36)
    display_order = models.SmallIntegerField(default=0)
    body = models.TextField()
    infos = models.JSONField(blank=True, default=Utility.relationship_infos, help_text='Example: {"owner": "John"}. Please keep {} here even no data', null=True)
    category = models.ForeignKey(db_constraint=False, help_text="subtype: for note it's public/counseling sub-types etc", on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.category')
    content_type = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='contenttypes.contenttype')
    organization = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.note')

    class Meta:
        db_table = 'persons_noteshistory'

