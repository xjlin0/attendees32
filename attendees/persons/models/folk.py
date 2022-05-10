import pghistory
from django.contrib.contenttypes.fields import GenericRelation
from uuid import uuid4
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Utility


class Folk(TimeStampedModel, SoftDeletableModel):
    """
    Model function as Family (category # 0) or other relationship (category # 25).

    For other relationship, primary attendee needs to be "hidden" role
    """
    id = models.UUIDField(default=uuid4, primary_key=True, editable=False, serialize=False)
    places = GenericRelation("whereabouts.Place")
    division = models.ForeignKey(
        "whereabouts.Division",
        default=0,
        null=False,
        blank=False,
        on_delete=models.SET(0),
    )
    category = models.ForeignKey(
        "persons.Category",
        null=False,
        blank=False,
        default=0,
        on_delete=models.SET(0),
        help_text="subtype: for folk, 0 is family and 25 is other",
    )
    attendees = models.ManyToManyField(
        "persons.Attendee", through="FolkAttendee", related_name="attendees"
    )
    display_name = models.CharField(max_length=50, blank=True, null=True)
    display_order = models.SmallIntegerField(
        default=0, blank=False, null=False, db_index=True
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.folk_infos,
        help_text='Example: {"pdf_export": False}. Please keep {} here even no data',
    )

    def __str__(self):
        return "%s %s %s" % (self.division, self.category, self.display_name)

    class Meta:
        db_table = "persons_folks"
        ordering = ("division", "category", "display_order", "-modified")
        indexes = [
            GinIndex(
                fields=["infos"],
                name="folk_infos_gin",
            ),
        ]


class FolksHistory(pghistory.get_event_model(
    Folk,
    pghistory.Snapshot('folk.snapshot'),
    name='FolksHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.folk')
    id = models.UUIDField(db_index=True, default=uuid4, editable=False, serialize=False)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    division = models.ForeignKey(db_constraint=False, default=0, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.division')
    is_removed = models.BooleanField(default=False)
    display_order = models.SmallIntegerField(default=0)
    infos = models.JSONField(blank=True, default=Utility.folk_infos, help_text='Example: {"pdf_export": False}. Please keep {} here even no data', null=True)
    category = models.ForeignKey(db_constraint=False, default=0, help_text='subtype: for folk, 0 is family and 25 is other', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.category')
    display_name = models.CharField(blank=True, max_length=50, null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = "persons_folkshistory"


