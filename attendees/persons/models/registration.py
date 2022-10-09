import pghistory
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
import django.utils.timezone
import model_utils.fields
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import Attendee, Note, Utility


class Registration(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    assembly = models.ForeignKey(
        "occasions.Assembly", on_delete=models.deletion.DO_NOTHING
    )
    registrant = models.ForeignKey(Attendee, null=True, on_delete=models.SET_NULL)
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text=('Example: {"price": "150.75", "donation": "85.00", "credit": "35.50", "apply_type": "online",'
                   '"apply_key": "001"}. Please keep {} here even no data',)
    )
    # Todo 20210619 Q: if assembly is Null, does that mean bad registration which cross organization?
    # @property
    # def price_sum(self):
    #     return sum([attending.price for attending in self.attending_set.all()]) + self.donation
    # # TODO: please check if attending_set works !!!!!!!!!
    #
    # def __str__(self):
    #     return '%s %s %s' % (self.apply_type, self.registrant, self.price_sum)

    def __str__(self):
        return "%s %s" % (self.registrant, self.assembly)

    @property
    def registrant_name(self):
        return self.registrant

    class Meta:
        db_table = "persons_registrations"
        ordering = ("assembly", "registrant__last_name", "registrant__first_name")
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "registrant"],
                condition=models.Q(is_removed=False),
                name="assembly_registrant",
            )
        ]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="registration_infos_gin",
            ),
        ]


class RegistrationsHistory(pghistory.get_event_model(
    Registration,
    pghistory.Snapshot('registration.snapshot'),
    pghistory.BeforeDelete('registration.before_delete'),
    name='RegistrationsHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='persons.registration')
    id = models.BigIntegerField(db_index=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    assembly = models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.assembly')
    infos = models.JSONField(blank=True, default=dict, help_text=('Example: {"price": "150.75", "donation": "85.00", "credit": "35.50", "apply_type": "online","apply_key": "001"}. Please keep {} here even no data',), null=True)
    registrant = models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='persons.attendee')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = "persons_registrationshistory"
