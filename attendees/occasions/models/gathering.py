# from django.core.exceptions import ValidationError
import pghistory, pytz
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility


class Gathering(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    meet = models.ForeignKey("Meet", on_delete=models.SET(0), null=False, blank=False)
    start = models.DateTimeField(null=False, blank=False, db_index=True)
    finish = models.DateTimeField(
        null=False, blank=False, help_text="Required for user to filter by time", db_index=True
    )
    attendings = models.ManyToManyField("persons.Attending", through="Attendance")
    display_name = models.CharField(
        max_length=255, blank=True, null=True, help_text="02/09/2020, etc"
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
        return (self.display_name or "") + (f" in {self.meet.display_name}" if self.meet.display_name else "")

    class Meta:
        db_table = "occasions_gatherings"
        ordering = ["meet", "start"]
        constraints = [
            models.UniqueConstraint(
                fields=["meet_id", "site_type", "site_id", "start"],
                condition=models.Q(is_removed=False),
                name="gathering_uniq_meet_location_time",
            )
        ]
        indexes = [
            models.Index(
                fields=["site_type", "site_id"],
                condition=models.Q(is_removed=False),
                name="gathering_sites",
            ),
            GinIndex(
                fields=["infos"],
                name="gathering_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s %s %s" % (
            self.meet,
            self.start,
            self.display_name or "",
            self.site or "",
        )

    # def time_and_location_dict(self, timezone='UTC', timeformat='%Y/%m/%d,%H:%M %p %Z'):
    #     return {
    #         "time": self.start.astimezone(pytz.timezone(timezone)).strftime(timeformat),
    #         "location": str(self.site),
    #     }


class GatheringsHistory(pghistory.get_event_model(
    Gathering,
    pghistory.Snapshot('gathering.snapshot'),
    name='GatheringsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.gathering')
    id = models.BigIntegerField(db_index=True)
    meet = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.meet')
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    start = models.DateTimeField()
    finish = models.DateTimeField(help_text='Required for user to filter by time')
    site_type = models.ForeignKey(db_constraint=False, help_text='site: django_content_type id for table name', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='contenttypes.contenttype')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"LG_location": "F207", "link": "https://..."}. Please keep {} here even no data', null=True)
    site_id = models.CharField(default='0', max_length=36)
    display_name = models.CharField(blank=True, help_text='02/09/2020, etc', max_length=255, null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_gatheringshistory'
