from datetime import datetime

from django.conf import settings
from django.db.models import F, Q, CharField, Value, When, Case
from django.db.models.functions import Concat, Trim
from rest_framework.utils import json
from attendees.occasions.models import Attendance, Meet
from attendees.persons.models import AttendingMeet
from attendees.persons.services import AttendeeService


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
    def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, gatherings, orderbys, photo_instead_of_gathering_assembly=False, search_value=None, search_expression=None, search_operation=None, filter=None):
        orderby_list = AttendanceService.orderby_parser(orderbys)
        extra_filters = Q(
            gathering__meet__assembly__division__organization=current_user.organization
        ).add(Q(gathering__meet__slug__in=meet_slugs), Q.AND)

        if gatherings:
            extra_filters.add(Q(gathering__in=gatherings), Q.AND)

        if character_slugs:  # attendance list UI prevent sending no character, but roll call UI will send no character
            extra_filters.add(Q(character__slug__in=character_slugs), Q.AND)

        # Todo 20220512 let scheduler see other attendings too?
        if not current_user.can_see_all_organizational_meets_attendees():
            extra_filters.add((Q(attending__attendee__in=current_user.attendee.scheduling_attendees())
                               |
                               Q(attending__registration__registrant=current_user.attendee)), Q.AND)

        if search_value and search_operation == 'contains' and search_expression == 'attending_label':  # only contains supported now
            extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
                               |
                               Q(attending__attendee__infos__icontains=search_value)), Q.AND)
        elif start:   # warning: attendance start&finish is optional, so limiting on gathering is needed in datagrid
            extra_filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
            extra_filters.add(Q(gathering__finish__gte=start), Q.AND)
        elif finish:  # but if user search in popup editor, relex time limits to allow adding future new ones.
            extra_filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)
            extra_filters.add(Q(gathering__start__lte=finish), Q.AND)

        if filter:  # only support single/double level so far
            filter_list = json.loads(filter)
            search_term = (filter_list[-1][-1]
                           if filter_list[1] == 'or'
                           else filter_list[0][0][-1]) if isinstance(filter_list[-1], list) else filter_list[-1]
            searching_by_panel = isinstance(search_term, str) and filter.count(search_term) == 3

            if isinstance(search_term, str) and searching_by_panel:
                extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_term)
                                   |
                                   Q(gathering__display_name__icontains=search_term)
                                   |
                                   Q(infos__icontains=search_term)
                                   |
                                   Q(attending__attendee__infos__icontains=search_term)), Q.AND)
            elif not searching_by_panel:  # it's grouping
                filters = AttendeeService.filter_parser(filter_list, Meet.objects.filter(slug__in=meet_slugs), current_user)
                extra_filters.add(filters, Q.AND)

        attendee_name = Trim(
            Concat(
                Trim(Concat("attending__attendee__first_name", Value(' '), "attending__attendee__last_name",
                            output_field=CharField())),
                Value(' '),
                Trim(Concat("attending__attendee__last_name2", "attending__attendee__first_name2",
                            output_field=CharField())),
                output_field=CharField()
            )
        )

        register_name = Trim(
            Concat(
                Trim(Concat("attending__registration__registrant__first_name", Value(' '),
                            "attending__registration__registrant__last_name", output_field=CharField())),
                Value(' '),
                Trim(Concat("attending__registration__registrant__last_name2",
                            "attending__registration__registrant__first_name2", output_field=CharField())),
                output_field=CharField()
            )
        )

        annotations = {
            'attending_name': Case(
                When(attending__registration__isnull=True, then=attendee_name),
                When(attending__registration__isnull=False, then=Concat(
                    attendee_name,
                    Value(' by '),
                    register_name,
                    output_field=CharField()
                )),
                output_field=CharField()
            )
        }

        if photo_instead_of_gathering_assembly:
            annotations['photo'] = Case(
                When(attending__attendee__photo='', then=Value(f"{settings.STATIC_URL}images/empty.png")),
                default=Concat(
                    Value('/private-media/'),
                    "attending__attendee__photo",
                    output_field=CharField()
                ),
                output_field=CharField()
            )
        else:
            annotations['gathering_name'] = Trim(
                Concat("gathering__display_name",
                       Value(' in '),
                       "gathering__meet__display_name",
                        output_field=CharField()))
            annotations['assembly'] = F("gathering__meet__assembly")
            annotations['meet'] = F("gathering__meet")

        return Attendance.objects.annotate(**annotations).filter(extra_filters).order_by(*orderby_list)

    @staticmethod
    def batch_create(begin, end, meet_slug, meet, user_time_zone):
        """
        Idempotently create attendances based on the following params and attendingmeet.

        :param begin:
        :param end:
        :param meet:
        :param meet_slug:
        :param user_time_zone:
        :return: number of attendances created
        """
        number_created = 0
        iso_time_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        user_begin_time = datetime.strptime(begin, iso_time_format)
        user_end_time = datetime.strptime(end, iso_time_format)

        if meet and user_end_time > user_begin_time:
            begin_time = (
                user_begin_time if meet.start < user_begin_time else meet.start
            ).astimezone(user_time_zone)
            end_time = (
                user_end_time if meet.finish > user_end_time else meet.finish
            ).astimezone(user_time_zone)

            for gathering in meet.gathering_set.filter(finish__gte=begin_time, start__lte=end_time):
                for attendingmeet in AttendingMeet.objects.filter(meet=meet, finish__gte=gathering.start, start__lte=gathering.finish):
                    attendance, attendance_created = Attendance.objects.get_or_create(
                        gathering=gathering,
                        attending=attendingmeet.attending,
                        character=attendingmeet.character,
                        team=attendingmeet.team,
                        defaults={
                            "gathering": gathering,
                            "attending": attendingmeet.attending,
                            "character": attendingmeet.character,
                            "team": attendingmeet.team,
                            "infos": meet.infos.get('attendance', {}),
                        },  # don't put time/place in attendance, since time/place may suddenly change by manager
                    )  # don't update attendance if exist since it may have customizations

                    if attendance_created:
                        number_created += 1

            results = {
                "success": True,
                "number_created": number_created,
                "meet_slug": meet.slug,
                "begin": begin_time,
                "end": end_time,
                "explain": "Please be aware that people can join the same gathering with different character and team.",
            }

        else:
            results = {
                "success": False,
                "number_created": number_created,
                "meet_slug": meet.slug if meet else meet_slug,
                "begin": begin,
                "end": end,
                "explain": "Meet or begin&end time invalid.",
            }

        return results

    @staticmethod
    def orderby_parser(orderbys):
        """
        generates sorter (column) based on user's choice
        :param orderbys: list of search params
        :return: a List of sorter for order_by()
        """
        orderby_dict = {}  # [{"selector":"<<dataField value in DataGrid>>","desc":false}]
        field_converter = {
            'gathering': 'gathering__display_name',
            'character': 'character__display_name',
            'attending': 'attending__attendee__infos__names__original',
        }

        for orderby in orderbys:
            raw_sort = orderby.get("selector", "id")
            field = (field_converter.get(raw_sort) if raw_sort in field_converter else raw_sort).replace(".", "__")
            direction = "-" if orderby.get("desc", False) else ""
            orderby_dict[direction + field] = True

        return orderby_dict.keys()
