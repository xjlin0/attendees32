from django.db import models
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from model_utils.models import TimeStampedModel, SoftDeletableModel

from attendees.persons.models import Utility, Note
from attendees.occasions.models import Gathering


class Property(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    places = GenericRelation('whereabouts.Place')
    gathering = GenericRelation(Gathering, object_id_field='site_id', content_type_field='site_type', related_query_name='property')
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    display_name = models.CharField(max_length=50, blank=False, null=False, db_index=True)
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    campus = models.ForeignKey('Campus', null=True, on_delete=models.SET_NULL)
    infos = JSONField(null=True, blank=True, default=dict, help_text='Example: {"2010id": "3"}. Please keep {} here even no data')

    class Meta:
        db_table = 'whereabouts_properties'
        verbose_name_plural = 'Properties'
        indexes = [
            GinIndex(fields=['infos'], name='property_infos_gin', ),
        ]

    def get_absolute_url(self):
        return reverse('property_detail', args=[str(self.id)])

    def __str__(self):
        return '%s %s %s' % (self.campus, self.display_name, self.places.all() and '; '.join([a.street for a in self.places.all()]) or '')
