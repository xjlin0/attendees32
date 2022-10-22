import logging
from datetime import timedelta

from django.db.models import F, Q, CharField, Value as V
from django.db.models.functions import Concat, Trim

from rest_framework.utils import json

from attendees.occasions.models import Meet
from attendees.persons.models import AttendingMeet, Attending, Utility

logger = logging.getLogger(__name__)


class AttendingMeetService:
    @staticmethod
    def flip_attendingmeet_by_existing_attending(current_user, attendees, meet_id, join=True):
        """
        If current_user has the permission, let attendees join/leave a meet. If there's no attending, create one
        attending.  Notice: This will overwrite existing attendingmeet, means mass assign will take higher priority
        of individual's previous attendingmeet.

        :param current_user:
        :param join: True is to join, false is to leave the meet
        :param attendees:
        :param meet_id:
        :return: attendingmeet results in the form of {attendee_id: attendingmeet object}
        """
        attendee_to_attendingmeets = {}
        meet = Meet.objects.filter(pk=meet_id).first()
        if meet:
            for attendee in attendees:
                if current_user.privileged_to_edit(attendee.id) or (current_user.attendee and current_user.attendee.can_schedule_attendee(attendee.id)):
                    attending = attendee.attendings.first()  # every attendee should already have an attending by signal
                    if join:
                        if not attending:
                            attending_attrs = {
                                'attendee': attendee,
                                'defaults': {
                                    'attendee': attendee,
                                    'infos': {},
                                }
                            }
                            logging.info(f"Because attending already auto-created upon attendee creation, creating attending for directory shouldn't happen for attendee id: {attendee.id}")
                            attending, attending_created = Attending.objects.update_or_create(**attending_attrs)

                        attendingmeet_attrs = {
                            'attending': attending,
                            'meet': meet,
                            'character': meet.major_character,
                        }

                        attendingmeet, attendingmeet_created = Utility.update_or_create_last(
                            AttendingMeet,
                            update=True,  # if attendee already joined before, don't change it
                            filters=attendingmeet_attrs,
                            defaults={**attendingmeet_attrs, 'finish': Utility.now_with_timezone() + timedelta(weeks=meet.infos.get('default_attendingmeet_in_weeks', 99999))},
                        )
                        attendee_to_attendingmeets[attendee] = attendingmeet
                    else:
                        AttendingMeet.objects.filter(
                            attending__in=attendee.attendings.all(),
                            meet=meet,
                            character=meet.major_character,
                            finish__gt=Utility.now_with_timezone()
                        ).update(finish=Utility.now_with_timezone())

                        attendee_to_attendingmeets[attendee] = None

        return attendee_to_attendingmeets

    @staticmethod
    def by_organization_meet_characters(current_user, meet_slugs, character_slugs, start, finish, orderbys, search_value=None, search_expression=None, search_operation=None, filter=None):
        orderby_list = AttendingMeetService.orderby_parser(orderbys)
        extra_filters = Q(
            meet__assembly__division__organization=current_user.organization
        ).add(Q(meet__slug__in=meet_slugs), Q.AND).add(Q(character__slug__in=character_slugs), Q.AND)
        # Todo 20220512 let scheduler see other attendings too?
        if not hasattr(current_user, 'attendee'):
            return []

        if not current_user.can_see_all_organizational_meets_attendees():
            extra_filters.add((Q(attending__attendee__in=current_user.attendee.scheduling_attendees())
                               |
                               Q(attending__registration__registrant=current_user.attendee)), Q.AND)

        if search_value and search_operation == 'contains' and search_expression == 'attending_label':  # for searching in drop down of popup editor
            extra_filters.add((Q(attending__registration__registrant__infos__icontains=search_value)
                               |
                               Q(attending__attendee__infos__icontains=search_value)), Q.AND)
        if filter:  # only support single/double level so far
            filter_list = json.loads(filter)
            search_term = (filter_list[-1][-1]
                           if filter_list[1] == 'or'
                           else filter_list[0][0][-1]) if isinstance(filter_list[-1], list) else filter_list[-1]
            if isinstance(search_term, str):  # for searching in the upper right search bar of datagrid
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
        return AttendingMeet.objects.annotate(
            register_name=Trim(
                Concat(
                    Trim(Concat("attending__registration__registrant__first_name", V(' '), "attending__registration__registrant__last_name", output_field=CharField())),
                    V(' '),
                    Trim(Concat("attending__registration__registrant__last_name2", "attending__registration__registrant__first_name2", output_field=CharField())),
                    output_field=CharField()
                )
            ),
            registrant_attendee_id=F("attending__registration__registrant_id"),
            attendee_id=F("attending__attendee_id"),
            attendee_name=F("attending__attendee__infos__names__original"),
            attendee_grade=F("attending__attendee__infos__fixed__grade"),
            # attendee_name=Trim(
            #     Concat(
            #         Trim(Concat("attending__attendee__first_name", V(' '), "attending__attendee__last_name", output_field=CharField())),
            #         V(' '),
            #         Trim(Concat("attending__attendee__last_name2", "attending__attendee__first_name2", output_field=CharField())),
            #         output_field=CharField()
            #     )
            # ),
            assembly=F("meet__assembly"),
        ).filter(extra_filters).order_by(*orderby_list)

    @staticmethod
    def orderby_parser(orderbys):
        """
        generates sorter (column) based on user's choice
        :param orderbys: list of search params
        :return: a List of sorter for order_by()
        """
        orderby_list = ([])  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]
        field_converter = {
            # 'team': 'team__display_name',  # cannot convert column for sort, or items will be out of order on grouping, since grouping use id and order using name!!
            'category': 'category__display_name',
            'character': 'character__display_name',
            'attending__attendee': 'attending__attendee__infos__names__original',
        }

        for orderby_dict in orderbys:
            raw_sort = orderby_dict.get("selector", "attending")
            field = (field_converter.get(raw_sort) if raw_sort in field_converter else raw_sort).replace(".", "__")
            direction = "-" if orderby_dict.get("desc", False) else ""
            orderby_list.append(direction + field)

        return orderby_list
