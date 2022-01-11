from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from . import Attendee, Note, Utility


class Registration(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    assembly = models.ForeignKey(
        "occasions.Assembly", null=True, on_delete=models.SET_NULL
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
