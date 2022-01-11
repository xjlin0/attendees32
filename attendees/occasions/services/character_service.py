from django.db.models import Case, Q, When

from attendees.occasions.models import Character
from attendees.persons.models import AttendingMeet


class CharacterService:
    @staticmethod
    def by_assembly_meets(assembly_slug, meet_slugs):
        return (
            Character.objects.filter(
                assembly__slug=assembly_slug,
                assembly__meet__slug__in=meet_slugs,
            )
            .order_by(
                "display_order",
            )
            .distinct()
        )

    @staticmethod
    def by_family_meets_gathering_intervals(user):
        """
        :query: Find all gatherings of all Attendances of the current user and their kid/care receiver, so all
                their "family" attendances gathering's characters (including not joined characters) will show up.
        :param user: the logged in user
        :return:  all Characters of the logged in user and their kids/care receivers' gathering.

        """
        return Character.objects.filter(
            Q(
                assembly__in=user.attendee.attendings.values_list(
                    "gathering__meet__assembly"
                )
            ),
            # |
            # Q(assembly__in=user.attendee.related_ones.filter(
            #     from_attendee__scheduler=True
            # ).values_list('attendings__gathering__meet__assembly')),
            assembly__division__organization__slug=user.organization.slug,
        ).order_by(
            "display_order",
        )  # another way is to get assemblys from registration, but it relies on attendingmeet validations

    @staticmethod
    def by_organization_assemblies(organization, assemblies, target_attendee):
        filters = {"assembly__division__organization": organization}
        if assemblies:
            filters["assembly__in"] = assemblies
        return Character.objects.filter(**filters).order_by(
            Case(
                When(
                    id__in=AttendingMeet.objects.filter(
                        attending__attendee=target_attendee
                    )
                    .values_list("character")
                    .distinct(),
                    then=0,
                ),
                default=1,
            ),
            "display_order",
        )

    # @staticmethod
    # def by_user_and_assembly(organization, assembly):
    #     filter_dict = dict(assembly__division__organization=organization)
    #     if assembly:
    #         filter_dict['assembly'] = assembly
    #
    #     return Character.objects.filter(**filter_dict).order_by(
    #         'display_order',
    #     )
