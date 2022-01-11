from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel


class Folk(UUIDModel, TimeStampedModel, SoftDeletableModel):
    """
    Model function as Family (category # 0) or other relationship (category # 25).

    For other relationship, primary attendee needs to be "hidden" role
    """

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
        default=dict,
        help_text='Example: {"2010id": "3"}. Please keep {} here even no data',
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
