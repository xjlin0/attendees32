from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
# from django.contrib.postgres.fields.jsonb import JSONField
from model_utils.models import SoftDeletableModel, TimeStampedModel
from schedule.models import EventRelation

from attendees.persons.models import Note, Utility


class Meet(TimeStampedModel, SoftDeletableModel, Utility):
    """
    Todo 20210823 currently one meet can only have single default location for all auto-generated gatherings, need
    to reconfirm if that's reality.  If one meet need to auto-generate gatherings with different default locations,
    we might need to store "{model name}#{integer id}" in EventRelation.distinction while sacrificing uuid models.

    """

    notes = GenericRelation(Note)
    event_relations = GenericRelation(EventRelation)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    assembly = models.ForeignKey(
        "occasions.Assembly", null=True, blank=True, on_delete=models.SET_NULL
    )
    attendings = models.ManyToManyField(
        "persons.Attending", through="persons.AttendingMeet", related_name="attendings"
    )
    major_character = models.ForeignKey(
        "occasions.Character", null=True, blank=True, on_delete=models.SET_NULL
    )
    shown_audience = models.BooleanField(
        "show AttendingMeet to participant?",
        null=False,
        blank=False,
        db_index=True,
        default=True,
        help_text="[some meets are only for internal records] show the AttendingMeet to attendee?",
    )
    audience_editable = models.BooleanField(
        "participant can edit AttendingMeet?",
        null=False,
        blank=False,
        default=True,
        help_text="[some meets are editable only by coworkers] participant can edit AttendingMeet?",
    )
    start = models.DateTimeField(
        null=False, blank=False, default=Utility.now_with_timezone
    )
    finish = models.DateTimeField(
        null=False, blank=False, help_text="Required for user to filter by time"
    )
    display_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        help_text="The Rock, Little Foot, singspiration, A/V control, etc.",
    )
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"info": "...", "url": "https://..."}. Please keep {} here even no data',
    )
    site_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET(0),
        help_text="site: django_content_type id for table name",
    )
    site_id = models.CharField(max_length=36, null=False, blank=False, default="0")
    site = GenericForeignKey("site_type", "site_id")

    # def save(self):
    #     pass # https://stackoverflow.com/a/27241824

    def get_absolute_url(self):
        return reverse("meet_detail", args=[str(self.id)])

    def info(self):
        return self.infos.get("info", "")

    def url(self):
        return self.infos.get("url", "")

    @property
    def schedule_rules(self):
        return [
            {
                "rule": er.event.rule.name,
                "start": er.event.start,
                "end": er.event.end,
                "location": Utility.get_location(er),
            }
            for er in self.event_relations.all()
        ]

    class Meta:
        db_table = "occasions_meets"

    def __str__(self):
        return "%s %s %s" % (
            self.display_name or "",
            self.infos.get("info", ""),
            self.infos.get("url", ""),
        )
