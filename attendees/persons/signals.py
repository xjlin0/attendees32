from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver
import pytz
from datetime import datetime
from partial_date import PartialDate
from attendees.occasions.models import Meet
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    FolkAttendee,
    Past,
    Utility,
)
from attendees.persons.services import AttendeeService


@receiver(post_save, sender=Past)
def post_save_handler_for_past_to_create_attendingmeet(sender, **kwargs):
    """
    To let user easily spot certain attendee attributes, here is automatic creation
    of AttendingMeet after creating Past of certain categories in Organization.infos

    :param sender: sender Class, Past
    :param kwargs:
    :return: None
    """
    if not kwargs.get("raw") and kwargs.get(  # to skip extra creation in loaddata seed
        "created"  # only when creating new, not for update
    ):
        created_past = kwargs.get("instance")
        organization = created_past.organization
        category_id = str(
            created_past.category.id
        )  # json can only have string as key, not numbers
        meet_id = (
            organization.infos.get("settings", {})
            .get("past_category_to_attendingmeet_meet", {})
            .get(category_id)
        )
        past_comment = created_past.infos.get("comment", "")
        if meet_id is not None and "importer" not in (past_comment or ''):  # skip for access importer
            meet = Meet.objects.filter(pk=meet_id).first()
            if meet:
                target_attendee = created_past.subject
                first_attending = target_attendee.attendings.first()
                if first_attending:
                    defaults = {
                        "character": meet.major_character,
                        "finish": Utility.forever(),
                    }
                    if isinstance(created_past.when, PartialDate) and created_past.when.date.year != 1800:
                        defaults["start"] = datetime.combine(created_past.when.date, datetime.max.time(), tzinfo=pytz.utc)
                    Utility.update_or_create_last(
                        AttendingMeet,
                        update=False,
                        filters={
                            "meet": meet,
                            "attending": first_attending,
                            "is_removed": False,
                            # "category_id": 6,  # Causing duplicates
                        },
                        defaults=defaults,
                    )


@receiver(post_save, sender=AttendingMeet)
def post_save_handler_for_attendingmeet_to_modify_folk(sender, **kwargs):
    """
    To let coworker easily create directory, here is automatic modification
    of Folk after creating AttendingMeet of certain meets in Meet.infos

    :param sender: sender Class, AttendingMeet
    :param kwargs:
    :return: None
    """
    if not kwargs.get("raw") and kwargs.get(  # to skip extra creation in loaddata seed
        "created"  # only when creating new, not for update
    ):
        created_attendingmeet = kwargs.get("instance")
        enabled = created_attendingmeet.meet.infos.get("automatic_modification", {}).get("Folk")
        created_from_folkattendee = "flip_attendingmeet_by_existing_attending" in created_attendingmeet.infos.get("created_reason", "")  # Some attendingmeet were auto created from new FolkAttendee whose Family already joined print directory
        if (
            enabled and created_attendingmeet.category_id != -1 and not created_from_folkattendee
        ):  # skip for access importer since special start date processing needed there
            target_attendee = created_attendingmeet.attending.attendee
            target_family = target_attendee.families.order_by('created').last()
            if target_family:
                target_family.infos['print_directory'] = created_attendingmeet.category.id == Attendee.SCHEDULED_CATEGORY
                target_family.save()

@receiver(post_save, sender=AttendingMeet)
def post_save_handler_for_attendingmeet_to_create_past(sender, **kwargs):
    """
    To let coworker easily spot certain attendee Past, here is automatic creation
    of Past after creating AttendingMeet of certain meets in Organization.infos

    :param sender: sender Class, AttendingMeet
    :param kwargs:
    :return: None
    """
    if not kwargs.get("raw") and kwargs.get(  # to skip extra creation in loaddata seed
        "created"  # only when creating new, not for update
    ):
        created_attendingmeet = kwargs.get("instance")
        organization = created_attendingmeet.meet.assembly.division.organization
        category_id = created_attendingmeet.meet.infos.get("automatic_creation", {}).get("Past")

        if (
            category_id and created_attendingmeet.category_id != -1
        ):  # skip for access importer since special start date processing needed there
            category = Category.objects.filter(pk=category_id).first()
            if category:
                target_attendee = created_attendingmeet.attending.attendee
                attendee_content_type = ContentType.objects.get_for_model(
                    target_attendee
                )
                defaults = {
                    "display_name": "Please update the date",
                    "when": None,  # AttendingMeet's start may not be actual date, ie. accept 30 years ago not remembering the date
                    "infos": {
                        **Utility.relationship_infos(),
                        "comment": "Auto created by AttendingMeet signal (not importer)",
                    },
                }

                Utility.update_or_create_last(
                    Past,
                    update=False,  # order_key='modified',  # Past id is UUID and out of order
                    filters={
                        "organization": organization,
                        "content_type": attendee_content_type,
                        "object_id": target_attendee.id,
                        "category": category,
                        "is_removed": False,
                    },
                    defaults=defaults,
                )


@receiver(post_save, sender=Attendee)
def post_save_handler_for_attendee_to_folk_and_attending(sender, **kwargs):
    """
    To let coworker easily create AttendingMeet/Past, here is automatic creation of non-family Folk and
    Attending after creating Attendee by settings from Organization.infos

    :param sender: sender Class, Attendee
    :param kwargs:
    :return: None
    """
    if not kwargs.get("raw") and kwargs.get(
        "created"
    ):  # to skip extra creation in loaddata seed
        created_attendee = kwargs.get("instance")
        organization = (
            created_attendee.division.organization
        )  # Maybe 0 in access importer

        AttendeeService.create_or_update_first_folk(
            created_attendee,
            f"{created_attendee.infos['names']['original']} other",
            Attendee.NON_FAMILY_CATEGORY,
            Attendee.HIDDEN_ROLE,
            False,
        )  # Todo 20211124: create family and relationship folks after save

        if "importer" not in created_attendee.infos.get(
            "created_reason", ""
        ) and organization.infos.get("settings", {}).get(
            "attendee_to_attending"
        ):  # skip for access importer

            defaults = {
                'category': 'auto-created',
                'infos': {
                    'created_reason': 'Auto created by Attendee save',
                },
            }

            Utility.update_or_create_last(
                Attending,
                update=False,  # order_key='modified',  # Past id is UUID and out of order
                filters={"attendee": created_attendee, "is_removed": False},
                defaults=defaults,
            )


@receiver(post_save, sender=FolkAttendee)
def post_save_handler_for_folkattendee_to_clear_unaccompanied_warning(sender, **kwargs):
    """
    When a parent/guardian is added to a family folk, auto clear the
    unaccompanied minor warning flag (infos['special']['check_in']) from the
    active attendingmeets of children in the same family.
    """
    if kwargs.get("raw"):
        return

    instance = kwargs.get("instance")
    if not instance or instance.is_removed:
        return

    folk = instance.folk
    if not folk or folk.category_id not in (Attendee.FAMILY_CATEGORY, Attendee.NON_FAMILY_CATEGORY):
        return

    role = instance.role
    is_guardian = False
    if role:
        is_guardian = (
            getattr(role, "emergency_contact", False)
            or (role.title and role.title.lower() in ["parent", "father", "mother", "guardian", "caregiver", "emergency_contact"])
        )

    if not is_guardian:
        return

    family_attendee_ids = list(
        FolkAttendee.objects.filter(
            folk=folk,
            is_removed=False,
        ).exclude(
            attendee_id=instance.attendee_id
        ).values_list("attendee_id", flat=True)
    )

    if not family_attendee_ids:
        return

    active_ams = AttendingMeet.objects.filter(
        attending__attendee_id__in=family_attendee_ids,
        is_removed=False,
    )
    for am in active_ams:
        if am.infos and isinstance(am.infos, dict) and "special" in am.infos:
            if isinstance(am.infos["special"], dict) and "check_in" in am.infos["special"]:
                del am.infos["special"]["check_in"]
                if not am.infos["special"]:
                    del am.infos["special"]
                am.save(update_fields=["infos"])


