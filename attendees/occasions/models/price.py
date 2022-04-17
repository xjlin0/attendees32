import pghistory
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MinValueValidator
from django.db import models
import django.utils.timezone
import model_utils.fields
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
    price_type = models.CharField(max_length=20, db_index=True, help_text="example: no bed_earlybird")
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


class PricesHistory(pghistory.get_event_model(
    Price,
    pghistory.Snapshot('price.snapshot'),
    name='PricesHistory',
    related_name='history',
)):
    pgh_id = models.AutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    pgh_label = models.TextField(help_text='The event label.')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to='occasions.price')
    id = models.BigIntegerField()
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    assembly = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='occasions.assembly')
    start = models.DateTimeField()
    finish = models.DateTimeField()
    price_type = models.CharField(max_length=20, help_text="example: no bed_earlybird")
    price_value = models.DecimalField(decimal_places=2, default=999999, max_digits=8, validators=[MinValueValidator(0)])
    display_name = models.CharField(max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'occasions_priceshistory'
