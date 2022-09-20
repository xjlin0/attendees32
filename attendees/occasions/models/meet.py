import pghistory, pytz
from datetime import datetime
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.contrib.contenttypes.models import ContentType
from django.db import models
import django.utils.timezone
import model_utils.fields
from django.urls import reverse
from django.conf import settings
from model_utils.models import SoftDeletableModel, TimeStampedModel
from schedule.models import EventRelation

from attendees.persons.models import Note, Utility


class Meet(TimeStampedModel, SoftDeletableModel, Utility):
    """
    Event is related by EventRelation with distinction 'source'.  The site_id/type here is just
    default, should copy to Event description as 'room#42', so one meet can have multiple Event
    happening at different sites.

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
        null=False, blank=False, default=Utility.now_with_timezone, db_index=True
    )
    finish = models.DateTimeField(
        null=False, blank=False, help_text="Required for user to filter by time", db_index=True
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
        default=Utility.meet_infos,
        help_text='Example: {"info": "...", "url": "https://..."}. Please keep {} here even no data',
    )
    site_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET(0),
        help_text="site: django_content_type id for table name",
    )
    site_id = models.CharField(max_length=36, null=False, blank=False, default="0")
    site = GenericForeignKey("site_type", "site_id")  # This is default, will copy over to Event.description

    # def save(self, *args, **kwargs):  # https://stackoverflow.com/a/27241824
    #     super(Meet, self).save(*args, **kwargs)  # One meet may have multiple Events

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

    def schedule_text(self, timezone_name=settings.TIME_ZONE, format='%H:%M%p %a'):
        schedules = [
            f"{datetime.strftime(er.event.start.astimezone(pytz.timezone(timezone_name)), format)}~{datetime.strftime(er.event.end.astimezone(pytz.timezone(timezone_name)), format)} {timezone_name},{er.event.rule.name}@{Utility.get_location(er)}"
            for er in self.event_relations.all()
        ]
        return ", ".join(schedules)

    class Meta:
        db_table = "occasions_meets"
        indexes = [
            models.Index(
                fields=["site_type", "site_id"],
                condition=models.Q(is_removed=False),
                name="meet_sites",
            ),
            GinIndex(
                fields=["infos"],
                name="meet_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s %s" % (
            self.display_name or "",
            self.infos.get("info", ""),
            self.infos.get("url", ""),
        )


class MeetsHistory(pghistory.get_event_model(
    Meet,
    pghistory.Snapshot('meet.snapshot'),
    name='MeetsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.meet')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    shown_audience = models.BooleanField(default=True, help_text='[some meets are only for internal records] show the AttendingMeet to attendee?', verbose_name='show AttendingMeet to participant?')
    audience_editable = models.BooleanField(default=True, help_text='[some meets are editable only by coworkers] participant can edit AttendingMeet?', verbose_name='participant can edit AttendingMeet?')
    start = models.DateTimeField(default=Utility.now_with_timezone)
    finish = models.DateTimeField(help_text='Required for user to filter by time')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"info": "...", "url": "https://..."}. Please keep {} here even no data', null=True)
    site_type = models.ForeignKey(db_constraint=False, help_text='site: django_content_type id for table name', on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='contenttypes.contenttype')
    slug = models.SlugField(db_index=False)
    site_id = models.CharField(default='0', max_length=36)
    assembly = models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.assembly')
    major_character = models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.character')
    display_name = models.CharField(blank=True, help_text='The Rock, Little Foot, singspiration, A/V control, etc.', max_length=50, null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_meetshistory'
