from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from attendees.occasions.models import Meet
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
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
    if not kwargs.get("raw") and kwargs.get(
        "created"
    ):  # to skip extra creation in loaddata seed
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
        if meet_id and "importer" not in created_past.infos.get(
            "comment", ""
        ):  # skip for access importer
            meet = Meet.objects.filter(pk=meet_id).first()
            if meet:
                target_attendee = created_past.subject
                first_attending = target_attendee.attendings.first()
                if first_attending:
                    defaults = {
                        "character": meet.major_character,
                        "finish": Utility.forever(),
                    }
                    if created_past.when:
                        defaults["start"] = created_past.when
                    Utility.update_or_create_last(
                        AttendingMeet,
                        update=False,
                        filters={
                            "meet": meet,
                            "attending": first_attending,
                            "is_removed": False,
                        },
                        defaults=defaults,
                    )


@receiver(post_save, sender=AttendingMeet)
def post_save_handler_for_attendingmeet_to_create_past(sender, **kwargs):
    """
    To let coworker easily spot certain attendee Past, here is automatic creation
    of Past after creating AttendingMeet of certain meets in Organization.infos

    :param sender: sender Class, AttendingMeet
    :param kwargs:
    :return: None
    """
    if not kwargs.get("raw") and kwargs.get(
        "created"
    ):  # to skip extra creation in loaddata seed
        created_attendingmeet = kwargs.get("instance")
        organization = created_attendingmeet.meet.assembly.division.organization
        meet_id = str(created_attendingmeet.meet.id)
        category_id = (
            organization.infos.get("settings", {})
            .get("attendingmeet_meet_to_past_category", {})
            .get(meet_id)
        )

        if (
            category_id and "importer" not in created_attendingmeet.category
        ):  # skip for access importer
            category = Category.objects.filter(pk=category_id).first()
            if category:
                target_attendee = created_attendingmeet.attending.attendee
                attendee_content_type = ContentType.objects.get_for_model(
                    target_attendee
                )
                defaults = {
                    "display_name": "activity added",
                    "when": None,  # AttendingMeet's start may not be actual date
                    "infos": {
                        **Utility.relationship_infos(),
                        "comment": "Auto created by AttendingMeet importer signal",
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
            f"{created_attendee.infos['names']['original']} general relationship",
            Attendee.NON_FAMILY_CATEGORY,
            Attendee.HIDDEN_ROLE,
        )

        if "importer" not in created_attendee.infos.get(
            "created_reason", ""
        ) and organization.infos.get("settings", {}).get(
            "attendee_to_attending"
        ):  # skip for access importer
            defaults = {
                "category": "auto-created",
                "infos": {
                    "created_reason": "Auto created by Attendee creation",
                },
            }

            Utility.update_or_create_last(
                Attending,
                update=False,  # order_key='modified',  # Past id is UUID and out of order
                filters={"attendee": created_attendee, "is_removed": False},
                defaults=defaults,
            )
            # Todo 20211124: create family and relationship folks after save
