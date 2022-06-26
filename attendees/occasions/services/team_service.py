from attendees.occasions.models import Team, Gathering


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
    def by_organization_meets(organization_slug, meet_slugs, pk=None, search_value=None, search_expression=None, search_operation=None, gathering=None):
        filters = {
            'meet__assembly__division__organization__slug': organization_slug,
        }

        if pk:
            filters['pk'] = pk
        else:
            if search_value and search_operation == 'contains':  # only contains supported now
                filters[f'{search_expression}__icontains'] = search_value

            if gathering:
                filters['meet'] = Gathering.objects.get(pk=gathering).meet

            if meet_slugs:
                if meet_slugs[0] and meet_slugs[0].isnumeric():
                    filters['meet__id__in'] = meet_slugs
                else:
                    filters['meet__slug__in'] = meet_slugs

        return Team.objects.filter(**filters).order_by(
            "display_order",
        )
