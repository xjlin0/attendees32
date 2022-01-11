from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.urls import reverse
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility


class Assembly(TimeStampedModel, SoftDeletableModel, Utility):
    places = GenericRelation("whereabouts.Place")
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    start = models.DateTimeField(null=True, blank=True, help_text="optional")
    finish = models.DateTimeField(null=True, blank=True, help_text="optional")
    # contacts = models.ManyToManyField('whereabouts.Place', through='AssemblyContact')
    category = models.CharField(
        max_length=20,
        default="normal",
        blank=False,
        null=False,
        db_index=True,
        help_text="normal, no-display, etc",
    )
    display_name = models.CharField(
        max_length=50,
        blank=False,
        null=False,
        help_text="Uniq within Organization, adding year helps",
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    slug = models.SlugField(
        max_length=50,
        blank=False,
        null=False,
        unique=True,
        help_text="format: Organization_name-Assembly_name",
    )
    need_age = models.BooleanField(
        "Does registration need age info?",
        null=False,
        blank=False,
        default=False,
        help_text="Does the age info of the participants required?",
    )
    division = models.ForeignKey(
        "whereabouts.Division", null=False, blank=False, on_delete=models.SET(0)
    )
    infos = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="please keep {} here even there's no data",
    )

    def get_absolute_url(self):
        return reverse("assembly_detail", args=[str(self.id)])

    class Meta:
        db_table = "occasions_assemblies"
        verbose_name_plural = "Assemblies"
        ordering = (
            "division",
            "display_order",
        )
        indexes = [
            GinIndex(
                fields=["infos"],
                name="assembly_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s" % self.display_name

    def get_addresses(self):
        return "\n".join([a.street for a in self.places.all() if a is not None])


# Todo 20210718 add uniq at save:  within organization, the display_name should be uniq for grouped dropdown
