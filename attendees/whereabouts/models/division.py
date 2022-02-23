from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.occasions.models import Gathering
from attendees.persons.models import Note, Utility

from . import Organization


class Division(TimeStampedModel, SoftDeletableModel, Utility):
    link_notes = GenericRelation(Note)
    gathering = GenericRelation(
        Gathering,
        object_id_field="site_id",
        content_type_field="site_type",
        related_query_name="division",
    )
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    organization = models.ForeignKey(
        Organization, null=False, blank=False, on_delete=models.SET(0)
    )
    display_name = models.CharField(max_length=50, blank=False, null=False, help_text='"Junior Ministry" is a magic word to show certain Attendee infos in attendee_update_view.js')
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    audience_auth_group = models.ForeignKey(
        "auth.Group",
        null=False,
        blank=False,
        help_text="which auth group does the joining general participant belong to?",
        on_delete=models.SET(0),
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"show_attendee_infos": {"insurer": true}}. Please keep {} here even no data',
    )
    #  Todo 20210529: rename division of "data" to "organizational"

    class Meta:
        db_table = "whereabouts_divisions"
        indexes = [
            GinIndex(
                fields=["infos"],
                name="division_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s" % self.display_name
