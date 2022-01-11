# from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
# from django.contrib.postgres.fields.jsonb import JSONField
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility


class Gathering(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    meet = models.ForeignKey("Meet", on_delete=models.SET(0), null=False, blank=False)
    start = models.DateTimeField(null=False, blank=False)
    finish = models.DateTimeField(
        null=False, blank=False, help_text="Required for user to filter by time"
    )
    attendings = models.ManyToManyField("persons.Attending", through="Attendance")
    display_name = models.CharField(
        max_length=50, blank=True, null=True, help_text="02/09/2020, etc"
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"LG_location": "F207", "link": "https://..."}. Please keep {} here even no data',
    )
    site_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET(0),
        help_text="site: django_content_type id for table name",
    )
    site_id = models.CharField(max_length=36, null=False, blank=False, default="0")
    site = GenericForeignKey("site_type", "site_id")

    # from itertools import groupby
    # from operator import attrgetter
    #
    # ordered_program_sessions = ProgramSession.objects.order_by('program_group', 'start_at')
    # program_sessions_grouped_by_program_groups = {
    #     k: list(v)
    #     for k, v in groupby(ordered_program_sessions, attrgetter('program_group'))
    # } #=> {<ProgramGroup: The Rock  >: [<ProgramSession: The Rock #1...>, <ProgramSession: The Rock #2...>]}

    def get_absolute_url(self):
        return reverse("gathering_detail", args=[str(self.id)])

    @property
    def gathering_label(self):
        return (self.meet.display_name or "") + " " + (self.display_name or "")

    class Meta:
        db_table = "occasions_gatherings"
        ordering = ["meet", "start"]
        constraints = [
            models.UniqueConstraint(
                fields=["meet_id", "site_type", "site_id", "start"],
                condition=models.Q(is_removed=False),
                name="uniq_meet_location_time",
            )
        ]

    def __str__(self):
        return "%s %s %s %s" % (
            self.meet,
            self.start,
            self.display_name or "",
            self.site or "",
        )
