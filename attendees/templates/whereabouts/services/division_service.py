from attendees.whereabouts.models import Division


class DivisionService:

    @staticmethod
    def by_organization(organization_slug):
        return Division.objects.filter(
            organization__slug=organization_slug,
        ).order_by(
            'display_name',
        )
