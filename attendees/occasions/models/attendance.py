from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility


class Attendance(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    start = models.DateTimeField(null=True, blank=True, help_text="optional")
    finish = models.DateTimeField(null=True, blank=True, help_text="optional")
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
    free = models.SmallIntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="multitasking: the person cannot join other gatherings if negative",
    )
    category = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        db_index=True,
        default="scheduled",
        help_text="RSVPed, leave, remote, etc",
    )
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"kid_points": 5}. Please keep {} here even no data',
    )

    def clean(self):
        if (
            self.character.assembly != self.gathering.meet.assembly
            or self.gathering.meet not in self.attending.meets.all()
        ):
            raise ValidationError(
                "The charater assembly, gathering's meet/assembly, and attendings meets needed to be matched,"
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
                fields=["gathering", "attending", "character", "team"],
                condition=models.Q(is_removed=False),
                name="gathering_attending_character_team",
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
