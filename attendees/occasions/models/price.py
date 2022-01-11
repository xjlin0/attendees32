from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel

from attendees.persons.models import Note, Utility

from . import Assembly


class Price(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    assembly = models.ForeignKey(Assembly, null=True, on_delete=models.SET_NULL)
    start = models.DateTimeField(null=False, blank=False)
    finish = models.DateTimeField(null=False, blank=False)
    display_name = models.CharField(max_length=50)
    price_type = models.CharField(max_length=20, db_index=True)
    price_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=999999,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "occasions_prices"

    def __str__(self):
        return "%s %s %s %s %s" % (
            self.assembly,
            self.display_name,
            self.start,
            self.price_type,
            self.price_value,
        )
