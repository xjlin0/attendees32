import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
import django.utils.timezone
import model_utils.fields
from django.utils.functional import cached_property
from model_utils.models import SoftDeletableModel, TimeStampedModel
from private_storage.fields import PrivateFileField
from private_storage.storage.files import PrivateFileSystemStorage

from attendees.persons.models import Note, Utility


class Attendance(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    start = models.DateTimeField(null=True, blank=True, help_text="optional", db_index=True)
    finish = models.DateTimeField(null=True, blank=True, help_text="optional", db_index=True)
    gathering = models.ForeignKey(
        "Gathering", null=False, blank=False, on_delete=models.SET(0)
    )
    team = models.ForeignKey(
        "Team",
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="empty for main meet",
    )
    attending = models.ForeignKey(
        "persons.Attending", null=False, blank=False, on_delete=models.SET(0)
    )
    character = models.ForeignKey(
        "Character", null=False, blank=False, on_delete=models.SET(0)
    )
    # free = models.SmallIntegerField(
    #     default=0,
    #     blank=True,
    #     null=True,
    #     help_text="multitasking: the person cannot join other gatherings if negative",
    # )
    category = models.ForeignKey(
        "persons.Category",
        default=1,  # scheduled
        blank=False,
        null=False,
        on_delete=models.SET(1),
        help_text="RSVPed, leave, remote, etc",
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"kid_points": 5}. Please keep {} here even no data',
    )
    file = PrivateFileField(
        "file", blank=True, null=True, upload_to="attendance_file"
    )  # https://github.com/edoburu/django-private-storage

    def clean(self):
        if (
            self.character.assembly != self.gathering.meet.assembly
            or self.gathering.meet not in self.attending.meets.all()
        ):
            raise ValidationError(
                "The character assembly, gathering's meet/assembly, and attendings meets needed to be matched,"
                "please pick another gathering, character or attending"
            )

    @cached_property
    def attendance_info(self):
        gathering = self.gathering
        return gathering.meet.display_name + gathering.start.strftime(" @ %b.%d'%y")

    def get_absolute_url(self):
        return reverse("attendance_detail", args=[str(self.id)])

    # @property
    # def gathering_label(self):
    #     return f'{self.gathering.meet.display_name} {self.gathering.display_name}'

    @property
    def attendance_label(self):
        return f"{self.attending.attendee.display_label}-{self.attending.main_contact.display_label}"

    # @property
    # def team_label(self):
    #     return self.team.display_name

    # @property
    # def character_label(self):
    #     return self.character.display_name

    class Meta:
        db_table = "occasions_attendances"
        constraints = [
            models.UniqueConstraint(
                fields=["gathering", "attending", "character", "team", "start"],
                condition=models.Q(is_removed=False),
                name="gathering_attending_character_team_start",
            )
        ]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="attendance_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s %s %s" % (
            self.gathering,
            self.character,
            self.attending,
            self.team or "",
        )


class AttendancesHistory(pghistory.get_event_model(
    Attendance,
    pghistory.Snapshot('attendance.snapshot'),
    pghistory.BeforeDelete('attendance.before_delete'),
    name='AttendancesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.attendance')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    display_order = models.SmallIntegerField(default=0)
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"kid_points": 5}. Please keep {} here even no data', null=True)
    attending = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.attending')
    character = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.character')
    gathering = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.gathering')
    category = models.ForeignKey(db_constraint=False, help_text="RSVPed, leave, remote, etc", default=1, on_delete=models.SET(1), related_name='+', related_query_name='+', to='persons.category')
    file = PrivateFileField(blank=True, null=True, storage=PrivateFileSystemStorage(), upload_to='attendance_file', verbose_name='file')
    team = models.ForeignKey(blank=True, db_constraint=False, default=None, help_text='empty for main meet', null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.team')
    start = models.DateTimeField(blank=True, help_text='optional', null=True)
    finish = models.DateTimeField(blank=True, help_text='optional', null=True)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_attendanceshistory'

