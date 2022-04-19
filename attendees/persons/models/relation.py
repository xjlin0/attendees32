import pghistory
from django.contrib.postgres.fields import ArrayField
import django.utils.timezone
import model_utils.fields
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import GenderEnum


class Relation(TimeStampedModel, SoftDeletableModel):
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    gender = models.CharField(
        max_length=11,
        blank=False,
        null=False,
        default=GenderEnum.UNSPECIFIED,
        choices=GenderEnum.choices(),
    )
    reciprocal_ids = ArrayField(
        verbose_name="corresponding relation ids",
        base_field=models.BigIntegerField(null=False, blank=False),
        default=list,
        blank=True,
        null=True,
        help_text="Have to be completely empty or in the shape of '1,2,3', no brackets",
    )
    title = models.CharField(
        "To be called", max_length=50, blank=False, null=False, unique=True
    )
    display_order = models.SmallIntegerField(
        default=0, blank=False, null=False, db_index=True
    )
    emergency_contact = models.BooleanField(
        "to be the emergency contact?",
        null=False,
        blank=False,
        default=False,
        help_text="default value, can be changed in relationships further",
    )
    scheduler = models.BooleanField(
        "to be the scheduler?",
        null=False,
        blank=False,
        default=False,
        help_text="default value, can view/change the schedules of the caller?",
    )
    relative = models.BooleanField(
        "relative?",
        null=False,
        blank=False,
        default=False,
        help_text="is it a relative?",
    )
    consanguinity = models.BooleanField(
        "blood relatives?",
        null=False,
        blank=False,
        default=False,
        help_text="is it blood relatives?",
    )

    def __str__(self):
        return "%s" % self.title

    class Meta:
        db_table = "persons_relations"
        ordering = (
            "display_order",
            "title",
        )


class RelationsHistory(pghistory.get_event_model(
    Relation,
    pghistory.Snapshot('relation.snapshot'),
    name='RelationsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.relation')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    display_order = models.SmallIntegerField(default=0)
    emergency_contact = models.BooleanField(default=False, help_text='default value, can be changed in relationships further', verbose_name='to be the emergency contact?')
    scheduler = models.BooleanField(default=False, help_text='default value, can view/change the schedules of the caller?', verbose_name='to be the scheduler?')
    relative = models.BooleanField(default=False, help_text='is it a relative?', verbose_name='relative?')
    consanguinity = models.BooleanField(default=False, help_text='is it blood relatives?', verbose_name='blood relatives?')
    reciprocal_ids = ArrayField(base_field=models.BigIntegerField(), blank=True, default=list, help_text="Have to be completely empty or in the shape of '1,2,3', no brackets", null=True, size=None, verbose_name='corresponding relation ids')
    gender = models.CharField(choices=GenderEnum.choices(), default=GenderEnum.UNSPECIFIED, max_length=11)
    title = models.CharField(max_length=50, verbose_name='To be called')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'persons_relationshistory'
