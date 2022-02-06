from datetime import date, datetime, timedelta, timezone
from partial_date import PartialDateField
import opencc
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
# from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from model_utils.models import SoftDeletableModel, TimeStampedModel, UUIDModel
from private_storage.fields import PrivateFileField
from unidecode import unidecode

from . import GenderEnum, Note, Utility


class Attendee(UUIDModel, Utility, TimeStampedModel, SoftDeletableModel):
    FAMILY_CATEGORY = 0
    NON_FAMILY_CATEGORY = 25
    HIDDEN_ROLE = 0
    # RELATIVES_KEYWORDS = ['parent', 'mother', 'guardian', 'father', 'caregiver']
    # to find attendee's parents/caregiver in cowokers view of all activities
    # AS_PARENT_KEYWORDS = ['notifier', 'caregiver']
    # BE_LISTED_KEYWORDS = ['care receiver']  # let the attendee's attendance showed in their parent/caregiver account
    pasts = GenericRelation("persons.Past")
    places = GenericRelation("whereabouts.Place")
    notes = GenericRelation(Note)
    # related_ones = models.ManyToManyField('self',through='Relationship',symmetrical=False,related_name='related_to')
    division = models.ForeignKey(
        "whereabouts.Division",
        default=0,
        null=False,
        blank=False,
        on_delete=models.SET(0),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # families = models.ManyToManyField('persons.Family', through='FamilyAttendee', related_name='families')
    folks = models.ManyToManyField(
        "persons.Folk", through="FolkAttendee", related_name="folks"
    )
    first_name = models.CharField(max_length=25, db_index=True, null=True, blank=True)
    last_name = models.CharField(max_length=25, db_index=True, null=True, blank=True)
    first_name2 = models.CharField(max_length=12, db_index=True, null=True, blank=True)
    last_name2 = models.CharField(max_length=8, db_index=True, null=True, blank=True)
    gender = models.CharField(
        max_length=11,
        blank=False,
        null=False,
        default=GenderEnum.UNSPECIFIED,
        choices=GenderEnum.choices(),
    )
    actual_birthday = models.DateField(blank=True, null=True)
    estimated_birthday = PartialDateField(null=True, help_text='1998, 1998-12 or 1992-12-31, please enter 1800 if year not known')
    deathday = models.DateField(blank=True, null=True)
    photo = PrivateFileField(
        "Photo", blank=True, null=True, upload_to="attendee_portrait"
    )  # https://github.com/edoburu/django-private-storage
    infos = models.JSONField(
        null=True,
        blank=True,
        default=Utility.attendee_infos,
        help_text='Example: {"fixed": {"food_pref": "peanut allergy", "nick_name": "John"}}.'
                  'Please keep {} here even no data',
    )

    @property
    def display_label(self):
        return (
            (self.first_name or "")
            + " "
            + (self.last_name or "")
            + " "
            + (self.last_name2 or "")
            + (self.first_name2 or "")
        )

    @property
    def division_label(self):
        return self.division.display_name if self.division else None

    # @property
    # def other_relations(self):
    #     return self.folks.exclude(category=self.FAMILY_CATEGORY)

    @property
    def related_ones(self):  # Todo: need filter on folkattendee finish_date?
        return self.__class__.objects.filter(folks__in=self.folks.all()).distinct()

    @property
    def families(self):
        return self.folks.filter(category=self.FAMILY_CATEGORY)

    # def related_ones(self, only_current=True, only_active=True, folk_category_limit_to=None):
    #     """
    #     :param only_current: if false, it will include expired folkattendee by existing finish date
    #     :param only_active: if false, it will include deleted folkattendees and folks
    #     :param folk_category_limit_to: to filter for a single int category id of folk
    #     :return: Attendee queryset
    #     """
    #     folk_filter = {}
    #
    #     if folk_category_limit_to:
    #         folk_filter['category'] = folk_category_limit_to
    #
    #     if only_active:
    #         folk_filter['is_removed'] = False
    #
    #     filters = Q(
    #         folkattendee__folk__in=self.folks.filter(**folk_filter)
    #     )
    #
    #     if only_active:  # cannot combine with above
    #         filters = filters & Q(folkattendee__is_removed=False)
    #
    #     if only_current:
    #         expire_filter = (
    #             Q(folkattendee__finish__isnull=True)
    #             |
    #             Q(folkattendee__finish__gte=datetime.now(timezone.utc))
    #         )
    #         filters = filters & expire_filter
    #
    #     return self.__class__.objects.filter(filters).distinct()

    @property
    def all_related_members(self):
        return self.__class__.objects.filter(
            Q(folks__in=self.folks.filter(category=self.FAMILY_CATEGORY))
            | Q(  # self.folks.all() will include relationships of others
                folks__in=self.folks.filter(
                    folkattendee__role=self.HIDDEN_ROLE
                ).exclude(category=self.FAMILY_CATEGORY)
            ),
        ).distinct()

    @property
    def other_relation_members(self):
        return self.__class__.objects.filter(
            folks__in=self.folks.filter(folkattendee__role=self.HIDDEN_ROLE).exclude(
                category=self.FAMILY_CATEGORY
            )
        ).distinct()  # HIDDEN_ROLE indicates the relationship of the attendee, not others

    @cached_property
    def family_members(self):
        return self.__class__.objects.filter(
            folks__in=self.folks.filter(category=self.FAMILY_CATEGORY)
        ).distinct()

    @cached_property
    def self_phone_numbers(self):
        return self.self_addresses_for_fields_of(["phone1", "phone2"])

    @cached_property
    def self_email_addresses(self):
        return self.self_addresses_for_fields_of(["email1", "email2"])

    def self_addresses_for_fields_of(self, fields):
        contacts = self.infos.get("contacts", {})
        return ", ".join(
            [contacts.get(field) for field in fields if contacts.get(field)]
        )

    @cached_property
    def caregiver_email_addresses(self):
        return self.caregiver_addresses_for_fields_of(["email1", "email2"])

    @cached_property
    def caregiver_phone_numbers(self):
        return self.caregiver_addresses_for_fields_of(["phone1", "phone2"])

    def caregiver_addresses_for_fields_of(self, fields):
        return ", ".join(
            set(
                a.self_addresses_for_fields_of(fields)
                for a in self.get_relative_emergency_contacts()
            )
        )

    def get_relative_emergency_contacts(self):
        return self.__class__.objects.filter(
            pk__in=[
                k for (k, v) in self.infos.get("emergency_contacts", {}).items() if v
            ]
        )
        # self.related_ones.filter(
        #     to_attendee__relation__relative=True,
        #     to_attendee__relation__emergency_contact=True,
        #     to_attendee__finish__gte=datetime.now(timezone.utc),
        # )

    def under_same_org_with(self, other_attendee_id):
        if other_attendee_id:
            return Attendee.objects.filter(
                pk=other_attendee_id, division__organization=self.division.organization
            ).exists()
        return False

    def can_schedule_attendee(self, other_attendee_id):
        if str(self.id) == other_attendee_id:
            return True
        return Attendee.objects.filter(
            pk=other_attendee_id, infos__schedulers__contains={str(self.id): True}
        ).exists()
        # self.__class__.objects.filter(
        #     (Q(from_attendee__finish__isnull=True) | Q(from_attendee__finish__gt=Utility.now_with_timezone())),
        #     from_attendee__to_attendee__id=self.id,
        #     from_attendee__from_attendee__id=other_attendee_id,
        #     from_attendee__scheduler=True,
        #     from_attendee__is_removed=False,
        # ).exists()

    def scheduling_attendees(self):
        """
        :return: all attendees that can be scheduled by the attendee. For example, if a kid specified its
        parent by "scheduler" is true in its infos__schedulers, when calling parent_attendee.scheduling_attendees(),
        the kid will be returned, means the parent can change/see schedule of the kid.
        """
        return self.__class__.objects.filter(
            infos__schedulers__contains={str(self.id): True}
        )
        # self.__class__.objects.filter(
        #     Q(id=self.id)
        #     |
        #     Q(
        #         (Q(from_attendee__finish__isnull=True) | Q(from_attendee__finish__gt=Utility.now_with_timezone())),
        #         from_attendee__to_attendee__id=self.id,
        #         from_attendee__scheduler=True,
        #         from_attendee__is_removed=False,
        #     )
        # ).distinct()

    @cached_property
    def parents_notifiers_names(self):
        """
        :return: attendees' names of their parents/caregiviers
        """
        return ", ".join(
            list(
                self.get_relative_emergency_contacts().values_list(
                    "infos__names__original", flat=True
                )
            )
        )

    def age(self):
        birthday = self.actual_birthday or (self.estimated_birthday and self.estimated_birthday.date)
        try:
            if birthday:
                return (date.today() - birthday) // timedelta(days=365.2425)
            else:
                return None
        except Exception as e:
            print(
                self.__str__() + "'s birthday incorrect: ",
                birthday,
                ". Type: ",
                type(birthday),
                " exception: ",
                e,
            )
            return None

    def __str__(self):
        return self.display_label

    def clean(self):
        if not (
            self.last_name or self.last_name2 or self.first_name or self.first_name2
        ):
            raise ValidationError("You must specify at least a name")

    def get_absolute_url(self):
        return reverse("/persons/attendee_detail_view/", kwargs={"pk": self.pk})

    class Meta:
        db_table = "persons_attendees"
        ordering = ["last_name", "first_name"]
        indexes = [
            GinIndex(
                fields=["infos"],
                name="attendee_infos_gin",
            ),
            # GinIndex(fields=['progressions'], name='attendee_progressions_gin', ),
        ]

    def save(self, *args, **kwargs):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        name2 = f"{self.last_name2 or ''}{self.first_name2 or ''}".strip()
        both_names = f"{name} {name2}".strip()
        self.infos["names"]["original"] = both_names
        self.infos["names"]["romanization"] = unidecode(
            both_names
        ).strip()  # remove accents & get phonetic
        if self.division.organization.infos.get("settings", {}).get(
            "opencc_convert"
        ):  # Let search work in either language
            s2t_converter = opencc.OpenCC("s2t.json")
            t2s_converter = opencc.OpenCC("t2s.json")
            self.infos["names"]["traditional"] = s2t_converter.convert(both_names)
            self.infos["names"]["simplified"] = t2s_converter.convert(both_names)
        super(Attendee, self).save(*args, **kwargs)

    def all_names(self):
        return [
            self.first_name,
            self.last_name,
            self.last_name2,
            self.first_name2,
        ] + list(self.infos["names"].values())

    # class ReadonlyMeta:
    #     readonly = ["full_name"]  # generated column
