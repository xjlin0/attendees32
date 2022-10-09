import pghistory
from django.core.exceptions import ValidationError
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import Utility


class AttendingMeet(TimeStampedModel, SoftDeletableModel, Utility):
    """
    Served as a partial template for attendance
    """

    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    attending = models.ForeignKey(
        "Attending", on_delete=models.SET(0), null=False, blank=False
    )
    meet = models.ForeignKey(
        "occasions.Meet", on_delete=models.SET(0), null=False, blank=False
    )
    start = models.DateTimeField(
        null=False, blank=False, db_index=True, default=Utility.now_with_timezone
    )
    finish = models.DateTimeField(
        null=False,
        blank=False,
        db_index=True,
        help_text="Required for user to filter by time",
    )
    team = models.ForeignKey(
        "occasions.Team",
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="empty for main meet",
    )
    character = models.ForeignKey(
        "occasions.Character", null=False, blank=False, on_delete=models.SET(0)
    )
    # category = models.CharField(
    #     max_length=20,
    #     default="primary",
    #     blank=False,
    #     null=False,
    #     help_text="primary, secondary, etc (primary will be displayed first)",
    # )
    category = models.ForeignKey(
        "persons.Category",
        default=1,  # scheduled
        blank=False,
        null=False,
        on_delete=models.SET(1),
        help_text="primary, secondary, etc (primary will be displayed first)",
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"kid_points": 5, "pdf_folks": ["uuid1"]}. Please keep {} here even no data',
    )

    def clean(self):
        if (
            not self.attending.registration.assembly
            == self.meet.assembly
            == self.character.assembly
        ):
            raise ValidationError(
                "The attending meet's assembly, registered assembly and character's assembly needed to be the same, "
                "please pick another registration, character or meet "
            )

    class Meta:
        db_table = "persons_attending_meets"
        constraints = [
            models.UniqueConstraint(
                fields=["meet", "attending", "character", "team"],
                condition=models.Q(is_removed=False),
                name="attending_meet_uniq",
            )
        ]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="attendingmeet_infos_gin",
            ),
        ]

    def __str__(self):
        return "%s %s" % (self.attending, self.meet)

    @staticmethod
    def check_participation_of(attendee, meet):
        return AttendingMeet.objects.filter(
                meet=meet,
                attending__attendee=attendee,
                finish__gte=Utility.now_with_timezone()
        ).exists()


class AttendingMeetsHistory(pghistory.get_event_model(
    AttendingMeet,
    pghistory.Snapshot('attendingmeet.snapshot'),
    pghistory.BeforeDelete('attendingmeet.before_delete'),
    name='AttendingMeetsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.attendingmeet')
    id = models.BigIntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    start = models.DateTimeField(default=Utility.now_with_timezone)
    finish = models.DateTimeField(help_text='Required for user to filter by time')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"kid_points": 5, "pdf_folks": ["uuid1"]}. Please keep {} here even no data', null=True)
    meet = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.meet')
    attending = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.attending')
    character = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.character')
    category = models.ForeignKey(db_constraint=False, help_text="primary, secondary, etc (primary will be displayed first)", default=1, on_delete=models.SET(1), related_name='+', related_query_name='+', to='persons.category')
    team = models.ForeignKey(blank=True, db_constraint=False, default=None, help_text='empty for main meet', null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.team')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'persons_attending_meetshistory'
