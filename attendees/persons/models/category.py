# from django.contrib.postgres.fields.jsonb import JSONField
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
