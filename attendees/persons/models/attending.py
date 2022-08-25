import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
import django.utils.timezone
import model_utils.fields
from django.urls import reverse
from django.utils.functional import cached_property
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import Attendee, Note, Registration, Utility


class Attending(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    registration = models.ForeignKey(
        Registration, null=True, blank=True, on_delete=models.SET_NULL
    )
    price = models.ForeignKey(
        "occasions.Price", null=True, blank=True, on_delete=models.SET_NULL
    )
    attendee = models.ForeignKey(
        Attendee,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="attendings",
    )
    gatherings = models.ManyToManyField(
        "occasions.Gathering", through="occasions.Attendance"
    )
    category = models.CharField(
        max_length=20,
        null=False,
        blank=False,
        default="normal",
        help_text="normal, not_going, coworker, etc",
    )
    meets = models.ManyToManyField(
        "occasions.Meet", through="AttendingMeet", related_name="meets"
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"grade": 5, "age": 11, "bed_needs": 1, "mobility": 300}. Please keep {} here even no data',
    )
    # Todo: infos contains the following display data which are not for table join/query: age, bed_needs, mobility

    def clean(self):
        # fetching birthday from attendee record first
        # Todo: check if meets' assemblies under attendee's organization
        if (
            self.registration
            and self.registration.assembly.need_age
            and self.infos.bed_needs < 1
            and self.infos.age is None
        ):
            raise ValidationError("You must specify age for the participant")

    def get_absolute_url(self):
        return reverse("attending_detail", args=[str(self.id)])

    class Meta:
        db_table = "persons_attendings"
        ordering = ["registration"]
        constraints = [
            models.UniqueConstraint(
                fields=["attendee", "registration"],
                condition=models.Q(is_removed=False),
                name="attending_attendee_registration",
            )
        ]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="attending_infos_gin",
            ),
        ]

    @property
    def main_contact(self):
        return self.registration.registrant

    @cached_property
    def meet_names(self):
        return ",".join([d.display_name for d in self.meets.all()])

    @property
    def attending_label(self):  # parentheses needed in attendee_update_view.js for populateAttendingButtons?
        return f"{self.attendee.display_label} by {self.registration}" if self.registration else self.attendee.display_label

    @cached_property
    def all_addresses(self):
        return "; ".join([a.street for a in self.attendee.places.all()])

    def __str__(self):
        return "%s %s" % (self.attendee, self.meet_names)


class AttendingsHistory(pghistory.get_event_model(
    Attending,
    pghistory.Snapshot('attending.snapshot'),
    name='AttendingsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='persons.attending')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    attendee = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.attendee')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"grade": 5, "age": 11, "bed_needs": 1, "mobility": 300}. Please keep {} here even no data', null=True)
    category = models.CharField(default='normal', help_text='normal, not_going, coworker, etc', max_length=20)
    price = models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.price')
    registration = models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.registration')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'persons_attendingshistory'
