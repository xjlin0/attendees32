# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import Utility


class FolkAttendee(TimeStampedModel, SoftDeletableModel):
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    folk = models.ForeignKey(
        "persons.Folk", null=False, blank=False, on_delete=models.CASCADE
    )
    attendee = models.ForeignKey(
        "persons.Attendee", null=False, blank=False, on_delete=models.CASCADE
    )
    role = models.ForeignKey(
        "persons.Relation",
        related_name="role",
        null=False,
        blank=False,
        on_delete=models.SET(0),
        verbose_name="attendee is",
        help_text="[Title] the family role of the attendee?",
    )
    display_order = models.SmallIntegerField(
        default=30000,
        blank=False,
        null=False,
        db_index=True,
        help_text="0 will be first family",
    )  # In current Attendee update page, FamilyAttendee order by created of family
    start = models.DateField(null=True, blank=True, help_text="date joining folk")
    finish = models.DateField(null=True, blank=True, help_text="date leaving folk")
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.relationship_infos,
        help_text='Example: {"show_secret": {"attendee1id": true, "attendee2id": false}}. Please keep {} here even no '
        "data",
    )  # compare to NoteAdmin

    def __str__(self):
        return "%s %s %s" % (self.folk, self.role, self.attendee)

    class Meta:
        db_table = "persons_folk_attendees"
        ordering = ("display_order",)
        constraints = [
            models.UniqueConstraint(
                fields=["folk", "attendee"],
                condition=models.Q(is_removed=False),
                name="folk_attendee",
            )
        ]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="folkattendee_infos_gin",
            ),
        ]
