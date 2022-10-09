from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CharField
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import validators
from django.utils.translation import ugettext_lazy as _
import pghistory
from schedule.models import CalendarRelation

from attendees.persons.models import Utility
from attendees.whereabouts.models import Organization


class User(AbstractUser):
    calendar_relations = GenericRelation(CalendarRelation)
    # First Name and Last Name do not cover name patterns around the globe.
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text="Primary organization of the user",
    )
    infos = models.JSONField(
        default=Utility.user_infos,
        null=True,
        blank=True,
        help_text="please keep {} here even there's no data",
    )

    class Meta:
        indexes = [
            GinIndex(
                fields=["infos"],
                name="user_infos_gin",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip()
        if self.email and User.objects.filter(email__iexact=self.email).exclude(username=self.username).exists():
            raise ValidationError("Identical email exists!")
        super(User, self).save(*args, **kwargs)

    def organization_pk(self):
        return self.organization.pk if self.organization else None

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def belongs_to_groups_of(
        self, auth_group_names
    ):  # .in_bulk() might take more memory
        return self.groups.filter(name__in=auth_group_names).exists()

    def belongs_to_organization_of(self, organization_slug):
        if self.is_superuser:
            return True
        else:
            return self.organization and self.organization.slug == organization_slug

    def can_see_all_organizational_meets_attendees(self):
        if self.organization:
            return self.belongs_to_groups_of(
                self.organization.infos["groups_see_all_meets_attendees"]
            )
        else:
            return False

    def privileged(self):
        """
        check if user's in correct groups to see other's data without relationships, currently are data_admins or counselor group
        Does NOT check if current user and targeting user are in the same organization!!
        :return: boolean
        """
        if self.organization:
            privileged_groups = self.organization.infos.get(
                "data_admins", []
            ) + self.organization.infos.get("counselor", [])
            return self.belongs_to_groups_of(privileged_groups)
        return False

    def privileged_to_edit(self, other_attendee_id):
        """
        check if user's in correct groups to see other attendee data (under same organization) without relationships, currently are data_admins or counselor group
        :return: boolean
        """
        if other_attendee_id and self.organization:

            privileged_groups = self.organization.infos.get(
                "data_admins", []
            ) + self.organization.infos.get("counselor", [])
            return self.belongs_to_groups_of(
                privileged_groups
            ) and self.attendee.under_same_org_with(other_attendee_id)
        return False

    def is_data_admin(self):
        organization_data_admin_group = (
            self.organization.infos.get("data_admins", []) if self.organization else []
        )
        return self.belongs_to_groups_of(organization_data_admin_group)

    def is_counselor(self):
        organization_counselor_groups = (
            self.organization.infos.get("counselor", []) if self.organization else []
        )
        return self.belongs_to_groups_of(organization_counselor_groups)

    def attendee_uuid_str(self):
        return str(self.attendee.id) if hasattr(self, "attendee") else ""

    def attend_divisions_of(self, division_slugs):
        return (
            self.attendee
            and self.attendee.attending_set.filter(
                divisions__slug__in=division_slugs
            ).exists()
        )

    def belongs_to_divisions_of(self, division_slugs):
        # if self.is_superuser:
        #     return True
        # else:
        return (
            self.organization
            and self.organization.division_set.filter(slug__in=division_slugs).exists()
        )

    def belongs_to_organization_and_division(self, organization_slug, division_slug):
        if self.is_superuser:
            return True
        else:
            return (
                self.organization
                and self.organization.slug == organization_slug
                and self.organization.division_set.filter(slug=division_slug).exists()
            )

    def attended_divisions_slugs(self):
        if self.attendee:
            return self.attendee.attending_set.values_list("division__slug", flat=True)
        else:
            return []

    def allowed_url_names(self, menu_category="API"):
        return (
            self.groups.filter(
                menuauthgroup__menu__organization=self.organization,
                menuauthgroup__menu__category=menu_category,
            )
            .values_list("menuauthgroup__menu__url_name", flat=True)
            .distinct()
        )


class UserHistory(pghistory.get_event_model(
    User,
    pghistory.Snapshot('user.snapshot'),
    pghistory.BeforeDelete('user.before_delete'),
    name='UserHistory',
    related_name='history',
    exclude=['password'],
)):
    pgh_id = models.BigAutoField(primary_key=True, serialize=False)
    pgh_created_at = models.DateTimeField(auto_now_add=True)
    id = models.IntegerField(db_index=True)
    is_superuser = models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')
    is_staff = models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')
    organization = models.ForeignKey(blank=True, db_constraint=False, default=None, help_text='Primary organization of the user', null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', related_query_name='+', to='whereabouts.organization')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='date joined')
    pgh_obj = models.ForeignKey(db_constraint=False, on_delete=models.deletion.DO_NOTHING, related_name='history', to=settings.AUTH_USER_MODEL)
    # password = models.CharField(max_length=128, verbose_name='password')
    pgh_label = models.TextField(help_text='The event label.')
    username = models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, validators=[validators.UnicodeUsernameValidator()], verbose_name='username')
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='last login')
    pgh_context = models.ForeignKey(db_constraint=False, null=True, on_delete=models.deletion.DO_NOTHING, related_name='+', to='pghistory.context')
    email = models.EmailField(blank=True, max_length=254, verbose_name='email address')
    infos = models.JSONField(blank=True, default=Utility.user_infos, help_text="please keep {} here even there's no data", null=True)
    name = models.CharField(blank=True, max_length=255, verbose_name='Name of User')

    class Meta:
        db_table = "users_userhistory"
