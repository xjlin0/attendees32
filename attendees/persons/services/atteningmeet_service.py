from django.db.models import F, Q
from rest_framework.utils import json
from attendees.persons.models import AttendingMeet


class AttendingMeetService:

    @staticmethod
    def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, orderbys, search_value=None, search_expression=None, search_operation=None, filter=None):
        orderby_list = AttendingMeetService.orderby_parser(orderbys)
        extra_filters = Q(
            meet__assembly__division__organization=current_user.organization
        ).add(Q(meet__slug__in=meet_slugs), Q.AND).add(Q(character__slug__in=character_slugs), Q.AND)
        # Todo 20220512 let scheduler see other attenings too?
        if not current_user.can_see_all_organizational_meets_attendees():
            extra_filters.add(Q(attending__attendee=current_user.attendee), Q.AND)

        if search_value and search_operation == 'contains' and search_expression == 'attending_label':  # only contains supported now
            extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
                               |
                               Q(attending__attendee__infos__icontains=search_value)), Q.AND)

        if filter:  # only support single/double level so far
            filter_list = json.loads(filter)
            search_term = filter_list[-1][-1] if isinstance(filter_list[-1], list) else filter_list[-1]
            if isinstance(search_term, str):
                extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_term)
                                   |
                                   Q(category__display_name__icontains=search_term)
                                   |
                                   Q(infos__icontains=search_term)
                                   |
                                   Q(attending__attendee__infos__icontains=search_term)), Q.AND)

        if start:
            extra_filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
        if finish:
            extra_filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)
        return AttendingMeet.objects.annotate(assembly=F("meet__assembly")).filter(extra_filters).order_by(*orderby_list)

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
