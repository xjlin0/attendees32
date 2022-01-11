from attendees.occasions.models import Team


class TeamService:
    @staticmethod
    def by_assembly_meets(assembly_slug, meet_slugs):
        return Team.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__slug=assembly_slug,
        ).order_by(
            "display_order",
        )

    @staticmethod
    def by_organization_meets(organization_slug, meet_slugs):
        return Team.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization__slug=organization_slug,
        ).order_by(
            "display_order",
        )
