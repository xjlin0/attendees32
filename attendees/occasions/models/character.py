from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
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
    info = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=50, null=False, default="normal", db_index=True)

    def get_absolute_url(self):
        return reverse("character_detail", args=[str(self.id)])

    class Meta:
        db_table = "occasions_characters"
        ordering = ["assembly", "display_order"]

    def __str__(self):
        return "%s %s %s" % (self.display_name, self.type, self.info or "")
