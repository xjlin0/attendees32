# from django.contrib.postgres.fields.jsonb import JSONField
import pghistory
import django.utils.timezone
import model_utils.fields
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import SoftDeletableModel, TimeStampedModel


class Category(TimeStampedModel, SoftDeletableModel):
    id = models.BigAutoField(
        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
    )
    type = models.CharField(
        max_length=25,
        default="generic",
        db_index=True,
        blank=False,
        null=False,
        help_text="main type",
    )
    display_order = models.SmallIntegerField(
        default=0, blank=False, null=False, db_index=True
    )
    display_name = models.CharField(
        max_length=50, blank=False, null=False, db_index=True
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text='Example: {"icon": "home", "style": "normal"}. Please keep {} here even no data',
    )

    def __str__(self):
        return "%s %s" % (self.type, self.display_name)

    class Meta:
        db_table = "persons_categories"
        verbose_name_plural = "Categories"
        ordering = ("type", "display_order")
        indexes = [
            GinIndex(
                fields=["infos"],
                name="category_infos_gin",
            ),
        ]


class CategoriesHistory(pghistory.get_event_model(
    Category,
    pghistory.Snapshot('category.snapshot'),
    name='CategoriesHistory',
    related_name='history',
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    created = model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')
    modified = model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')
    is_removed = models.BooleanField(default=False)
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.DO_NOTHING, related_name='history', to='persons.category')
    id = models.BigIntegerField()
    display_order = models.SmallIntegerField(default=0)
    pgh_label = models.TextField(help_text='The event label.')
    infos = models.JSONField(blank=True, default=dict, help_text='Example: {"icon": "home", "style": "normal"}. Please keep {} here even no data', null=True)
    type = models.CharField(default='generic', help_text='main type', max_length=25)
    display_name = models.CharField(max_length=50)
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')

    class Meta:
        db_table = 'persons_categorieshistory'
