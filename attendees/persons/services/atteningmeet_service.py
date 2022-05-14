from django.db.models import Q

from attendees.persons.models import AttendingMeet


class AttendingMeetService:

    @staticmethod
    def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, orderbys):
        orderby_list = AttendingMeetService.orderby_parser(orderbys)
        filters = Q(
            meet__assembly__division__organization__slug=current_user.organization.slug
        ).add(Q(meet__slug__in=meet_slugs), Q.AND).add(Q(character__slug__in=character_slugs), Q.AND)
        # Todo 20220512 let scheduler see other attenings too?
        if not current_user.can_see_all_organizational_meets_attendees():
            filters.add(Q(attending__attendee=current_user.attendee), Q.AND)

        if start:
            filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
        if finish:
            filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)
        return AttendingMeet.objects.filter(filters).order_by(*orderby_list)

    @staticmethod
    def orderby_parser(orderbys):
        """
        generates sorter (column) based on user's choice
        :param orderbys: list of search params
        :return: a List of sorter for order_by()
        """
        orderby_list = (
            []
        )  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]

        for orderby_dict in orderbys:
            field = orderby_dict.get("selector", "id").replace(".", "__")
            direction = "-" if orderby_dict.get("desc", False) else ""
            orderby_list.append(direction + field)

        return orderby_list
