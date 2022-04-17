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


class Character(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    assembly = models.ForeignKey(
        "Assembly", on_delete=models.SET(0), null=False, blank=False
    )
    display_name = models.CharField(
        max_length=50, blank=True, null=False, db_index=True
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    slug = models.SlugField(
        max_length=50,
        blank=False,
        null=False,
        unique=True,
        help_text="format: Assembly_name-Character_name",
    )
    infos = models.JSONField(blank=True, default=dict, help_text='example: {"info": "for distrubuting food"}, please keep {} here even there\'s no data', null=True)
    type = models.CharField(max_length=50, null=False, default="normal", db_index=True)

    def get_absolute_url(self):
        return reverse("character_detail", args=[str(self.id)])

    class Meta:
        db_table = "occasions_characters"
        ordering = ["assembly", "display_order"]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="character_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s %s" % (self.display_name, self.type, self.info or "")


class CharactersHistory(pghistory.get_event_model(
    Character,
    pghistory.Snapshot('character.snapshot'),
    name='Character',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.character')
    id = models.BigIntegerField()
    assembly = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.assembly')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    infos = models.JSONField(blank=True, default=dict, help_text='example: {"info": "for distrubuting food"}, please keep {} here even there\'s no data', null=True)
    display_order = models.SmallIntegerField(default=0)
    slug = models.SlugField(db_index=False, help_text='format: Assembly_name-Character_name')
    type = models.CharField(default='normal', max_length=50)
    display_name = models.CharField(blank=True, max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_charactershistory'
