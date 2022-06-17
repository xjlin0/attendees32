from django.db.models import F, Q, CharField, Value
from django.db.models.functions import Concat, Trim
from rest_framework.utils import json
from attendees.occasions.models import Attendance


class AttendanceService:
    @staticmethod
    def by_assembly_meets_characters_gathering_intervals(
        assembly_slug, meet_slugs, gathering_start, gathering_finish, character_slugs
    ):
        return (
            Attendance.objects.select_related()
            .filter(
                gathering__meet__assembly__slug=assembly_slug,
                gathering__meet__slug__in=meet_slugs,
                gathering__start__gte=gathering_start,
                gathering__finish__lte=gathering_finish,
                character__slug__in=character_slugs,
            )
            .order_by(
                "gathering__meet",
                "-gathering__start",
                "character__display_order",
            )
        )

    @staticmethod
    def by_organization_meets_gatherings_intervals(
        organization_slug, meet_slugs, gathering_ids, gathering_start, gathering_finish
    ):
        """
        :query: Find all gatherings of all Attendances of the current user, query everyone's
                Attendances in the found gatherings, so all coworker's Attendances in the
                current user participated gatherings will also show up.
        :param organization_slug:
        :param meet_slugs:
        :param gathering_ids: optional
        :param gathering_start:
        :param gathering_finish:
        :return:  user participation Attendances with coworkers Attendances
        """
        filters = {
            "gathering__meet__assembly__division__organization__slug": organization_slug,
            "gathering__meet__slug__in": meet_slugs,
            "gathering__start__gte": gathering_start,
            "gathering__finish__lte": gathering_finish,
        }

        if gathering_ids is not None:
            filters["gathering__id__in"] = gathering_ids

        return (
            Attendance.objects.select_related(
                "character",
                "team",
                "attending",
                "gathering",
                "attending__attendee",
            )
            .filter(**filters)
            .order_by(
                "gathering__meet",
                "-gathering__start",
                "character__display_order",
            )
        )

    @staticmethod
    def by_family_meets_gathering_intervals(
        admin_checking,
        attendee,
        current_user_organization,
        meet_slugs,
        gathering_start,
        gathering_finish,
    ):
        """
        :query: Find all gatherings of all Attendances of the current user and their kid/care receiver,
                , so all their "family" Attendances will show up.
        :param admin_checking:
        :param attendee:
        :param current_user_organization:
        :param meet_slugs:
        :param gathering_start:
        :param gathering_finish:

        :return:  Attendances of the logged in user and their kids/care receivers
        """
        extra_filters = {
            "gathering__meet__assembly__division__organization": current_user_organization,
            "gathering__meet__slug__in": meet_slugs,
            "gathering__start__lte": gathering_finish,
            "gathering__finish__gte": gathering_start,
        }

        if not admin_checking:
            extra_filters["gathering__meet__shown_audience"] = True

        return (
            Attendance.objects.select_related(
                "character",
                "team",
                "attending",
                "gathering",
                "attending__attendee",
            )
            .filter(
                Q(attending__attendee=attendee),
                # |
                # Q(attending__attendee__in=Relationship.objects.filter(
                #     to_attendee=attendee,
                #     scheduler=True
                # ).values_list('from_attendee')),
                **extra_filters
            )
            .order_by(
                "gathering__meet",
                "-gathering__start",
                "character__display_order",
            )
        )

    @staticmethod
    def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, orderbys, search_value=None, search_expression=None, search_operation=None, filter=None):
        orderby_list = AttendanceService.orderby_parser(orderbys)
        extra_filters = Q(
            gathering__meet__assembly__division__organization=current_user.organization
        ).add(Q(gathering__meet__slug__in=meet_slugs), Q.AND).add(Q(character__slug__in=character_slugs), Q.AND)
        # Todo 20220512 let scheduler see other attendings too?
        if not current_user.can_see_all_organizational_meets_attendees():
            extra_filters.add(Q(attending__attendee=current_user.attendee), Q.AND)
        print("hi 132 here is filter: ", filter)
        # if search_value and search_operation == 'contains' and search_expression == 'attending_label':  # only contains supported now
        #     extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
        #                        |
        #                        Q(attending__attendee__infos__icontains=search_value)), Q.AND)
        print("hi 137 here is orderby: ", orderbys)
        print("hi 138 here is orderby_list: ", orderby_list)
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
        return Attendance.objects.annotate(
            register_name=Trim(
                Concat(
                    Trim(Concat("attending__registration__registrant__first_name", Value(' '),
                                "attending__registration__registrant__last_name", output_field=CharField())),
                    Value(' '),
                    Trim(Concat("attending__registration__registrant__last_name2",
                                "attending__registration__registrant__first_name2", output_field=CharField())),
                    output_field=CharField()
                )
            ),
            attendee_name=Concat(
                Trim(Concat("attending__attendee__first_name", Value(' '), "attending__attendee__last_name",
                            output_field=CharField())),
                Value(' '),
                Trim(Concat("attending__attendee__last_name2", "attending__attendee__first_name2",
                            output_field=CharField())),
                output_field=CharField()
            ),
            gathering_name=Trim(
                Concat("gathering__meet__display_name",
                       Value(': '),
                       "gathering__display_name",
                        output_field=CharField())),
            assembly=F("gathering__meet__assembly"),
        ).filter(extra_filters).order_by(*orderby_list)

    @staticmethod
    def orderby_parser(orderbys):
        """
        generates sorter (column) based on user's choice
        :param orderbys: list of search params
        :return: a List of sorter for order_by()
        """
        orderby_list = (  # Todo 20220605 use Set instead of List to make it uniq
            []
        )  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]

        for orderby_dict in orderbys:
            field = orderby_dict.get("selector", "id").replace(".", "__")
            direction = "-" if orderby_dict.get("desc", False) else ""
            orderby_list.append(direction + field)

        return orderby_list
