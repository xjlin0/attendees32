from django.contrib.postgres.fields import ArrayField
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import GenderEnum


# @pghistory.track(
#     pghistory.Snapshot('relation.snapshot'),
#     model_name='RelationsHistory',
#     related_name='history',
# )
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
