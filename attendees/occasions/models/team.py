# from django.contrib.postgres.fields.jsonb import JSONField
import pghistory
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel
from django.contrib.postgres.indexes import GinIndex
import django.utils.timezone
import model_utils.fields
from attendees.persons.models import Note, Utility


class Team(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    meet = models.ForeignKey("Meet", null=False, blank=False, on_delete=models.SET(0))
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    display_name = models.CharField(max_length=50, blank=True, null=True)
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"link": "https://..."}. Please keep {} here even no data',
    )
    site_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET(0),
        help_text="site: django_content_type id for table name",
    )
    site_id = models.CharField(max_length=36, null=False, blank=False, default="0")
    site = GenericForeignKey("site_type", "site_id")

    class Meta:
        db_table = "occasions_teams"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="team_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s" % (self.meet, self.display_name or "")


class TeamsHistory(pghistory.get_event_model(
    Team,
    pghistory.Snapshot('team.snapshot'),
    name='TeamsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.team')
    id = models.BigIntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    meet = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.meet')
    display_order = models.SmallIntegerField(default=0)
    site_type = models.ForeignKey(db_constraint=False, help_text='site: django_content_type id for table name', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='contenttypes.contenttype')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"link": "https://..."}. Please keep {} here even no data', null=True)
    site_id = models.CharField(default='0', max_length=36)
    slug = models.SlugField(db_index=False)
    display_name = models.CharField(blank=True, max_length=50, null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_teamshistory'
