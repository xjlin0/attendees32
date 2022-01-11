from django.db import models
from django.urls import reverse
from django.contrib.contenttypes.fields import GenericRelation
from model_utils.models import TimeStampedModel, SoftDeletableModel

from attendees.persons.models import Utility, Note
from attendees.occasions.models import Gathering


class Suite(TimeStampedModel, SoftDeletableModel, Utility):
    notes = GenericRelation(Note)
    gathering = GenericRelation(Gathering, object_id_field='site_id', content_type_field='site_type', related_query_name='suite')
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    display_name = models.CharField(max_length=50, blank=False, null=False, db_index=True)
    slug = models.SlugField(max_length=50, blank=False, null=False, unique=True)
    property = models.ForeignKey('Property', null=True, on_delete=models.SET_NULL)
    site = models.CharField(max_length=50, blank=True, help_text='2F floor, etc')

    class Meta:
        db_table = 'whereabouts_suites'

    def get_absolute_url(self):
        return reverse('suite_detail', args=[str(self.id)])

    def __str__(self):
        return '%s %s %s' % (self.property.display_name, self.display_name, self.site or '')
