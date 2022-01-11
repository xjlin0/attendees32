from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel

from . import Utility  # , Note


class Past(UUIDModel, TimeStampedModel, SoftDeletableModel, Utility):
    """
    Model to store Note/Status/Education, etc. Need to implement audience permissions. For example,
    coworker A wrote some notes of user B, however these notes may/should not be shared with user B.
    One potential way is to have infos similar to infos__show_secret__all_counselors_: True
    infos__show_secret__ATTENDEE: True so whoever can access to attendee, including user B, can see it
    infos__show_secret__COWORKER or ORGANIZER: True so only coworker/organizer, not user B, can see it
    """

    COUNSELING = "counseling"  # for private data, and only assigned counselors
    ALL_COUNSELORS = (
        "all_counselors_"  # for private data, but accessible to all counselors
    )
    # notes = GenericRelation(Note)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=False, blank=False
    )
    object_id = models.CharField(max_length=36, null=False, blank=False)
    subject = GenericForeignKey("content_type", "object_id")
    when = models.DateTimeField(
        null=True, blank=True, default=Utility.now_with_timezone
    )
    finish = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(
        "persons.Category",
        null=False,
        blank=False,
        on_delete=models.SET(0),
        help_text="subtype: for education it's primary/high/college sub-types etc",
    )
    display_order = models.SmallIntegerField(
        default=30000, blank=False, null=False, db_index=True
    )
    display_name = models.CharField(max_length=50, blank=True, null=True)
    organization = models.ForeignKey(
        "whereabouts.Organization", null=False, blank=False, on_delete=models.SET(0)
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.relationship_infos,
        help_text=('Example: {"show_secret": {"attendee1id": true, "attendee2id": false}}.'
                   'Please keep {} here even no data',)
    )  # compare to NoteAdmin

    class Meta:
        db_table = "persons_pasts"
        ordering = (
            "organization",
            "category__type",
            "display_order",
            "category__display_order",
            "when",
        )
        indexes = [
            GinIndex(
                fields=["infos"],
                name="past_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s %s" % (self.subject, self.category, self.display_name)
