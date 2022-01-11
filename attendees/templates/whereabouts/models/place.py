from address.models import AddressField

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex
from model_utils.models import TimeStampedModel, SoftDeletableModel, UUIDModel

from attendees.persons.models import Utility


class Place(UUIDModel, TimeStampedModel, SoftDeletableModel, Utility):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, default=0, null=False, blank=False)
    object_id = models.CharField(max_length=36, null=False, blank=False, default='0')
    subject = GenericForeignKey('content_type', 'object_id')
    organization = models.ForeignKey('whereabouts.Organization', default=0, null=False, blank=False, on_delete=models.SET(0))
    address = AddressField(related_name='place', blank=True, null=True)
    # address_extra = models.CharField(max_length=50, blank=True, null=True, help_text='i.e. Apartment number')
    # address_type = models.CharField(max_length=20, default='street', blank=True, null=True, help_text='mailing, remote or street address')
    display_name = models.CharField(db_index=True, max_length=50, default='main', blank=False, null=False, help_text='main, resident, etc (main will be displayed first)')
    display_order = models.SmallIntegerField(default=0, blank=False, null=False)
    start = models.DateField(null=True, blank=True, help_text='optional, moved in date')
    finish = models.DateField(null=True, blank=True, help_text='optional, moved out date')
    infos = JSONField(default=Utility.default_infos, null=True, blank=True, help_text="please keep {} here even there's no data")
    # need to validate there only one 'main' for display_name

    class Meta:
        db_table = 'whereabouts_places'
        ordering = ('organization', 'content_type', 'object_id', 'display_order',)
        constraints = [
            models.UniqueConstraint(fields=['organization', 'content_type', 'object_id', 'address'], condition=models.Q(is_removed=False), name="address_object")
        ]
        indexes = [
            GinIndex(fields=['infos'], name='place_infos_gin', ),
        ]

    @property
    def street(self):
        return str(self.address)
        # if self.address:
        #     if Utility.blank_check(self.address_extra) and Utility.present_check(self.address.formatted):
        #         txt = '%s' % self.address.formatted
        #     elif self.address.locality:
        #         txt = ''
        #         if self.address.street_number:
        #             txt = '%s' % self.address.street_number
        #         if self.address.route:
        #             if txt:
        #                 txt += ' %s' % self.address.route
        #         if self.address_extra:
        #             txt = txt + ' %s' % self.address_extra if txt else ' %s' % self.address_extra
        #         locality = '%s' % self.address.locality
        #         if txt and locality:
        #             txt += ', '
        #         txt += locality
        #     else:
        #         txt = '%s' % self.address.raw
        #     return txt
        # else:
        #     return self.address_extra

    def __str__(self):
        return '%s %s' % (self.address, self.subject)
