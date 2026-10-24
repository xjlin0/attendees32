import re
from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from partial_date import PartialDate
import pghistory
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates.general import StringAgg, JSONBAgg
from django.db import transaction
from django.db.models import Case, F, Func, Q, When, CharField, JSONField, Count, Min
from django.db.models.functions import Cast, Substr, Coalesce
from django.db.models.expressions import OrderBy, Value
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.utils import json

from attendees.occasions.models import Attendance, Character, Gathering, Meet
from attendees.persons.models.enum import GenderEnum
from attendees.persons.models import (  # , Relationship
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    Folk,
    FolkAttendee,
    Registration,
    Relation,
    Utility, Past)
from attendees.persons.services import AttendingService, FolkService
from attendees.whereabouts.models import Division
from attendees.whereabouts.services import PlaceService


class AttendeeService:
    @staticmethod
    def by_assembly_meets(assembly_slug, meet_slugs):
        return Attendee.objects.filter(
            attendings__meets__slug__in=meet_slugs,
            attendings__meets__assembly__slug=assembly_slug,
        ).order_by("last_name", "last_name2", "first_name", "first_name2")

    @staticmethod
    def get_related_ones_by_permission(current_user, checking_attendee_id):
        """
        data admin can check all attendee and their related_ones. User can check other attendee if user
        is that attendee's scheduler
        :param current_user: current_user
        :param checking_attendee_id: the attendee_id requested
        :return: user's related attendees if no attendee id provided, or the requested related attendees if by
                 scheduler, or empty set.
        """
        user_attendee = Attendee.objects.filter(user=current_user).first()

        if user_attendee:
            user_checking_id = checking_attendee_id or user_attendee.id
            if current_user.privileged:
                return (
                    Attendee.objects.filter(
                        Q(id=user_checking_id)
                        | Q(
                            from_attendee__to_attendee__id=user_checking_id,
                            from_attendee__scheduler=True,
                        )
                        # Todo: add all families for data managers
                    )
                    .distinct()
                    .order_by(
                        OrderBy(
                            Func(F("id"), function="'{}'=".format(user_checking_id)),
                            descending=True,
                        ),
                        "infos__names__original",
                    )
                )
            else:
                return (
                    Attendee.objects.filter(
                        Q(id=user_attendee.id)
                        | Q(
                            from_attendee__to_attendee__id=user_attendee.id,
                            from_attendee__scheduler=True,
                        )
                    )
                    .distinct()
                    .order_by(
                        OrderBy(
                            Func(F("id"), function="'{}'=".format(user_attendee.id)),
                            descending=True,
                        ),
                        "infos__names__original",
                    )
                )

        else:
            raise Http404("Your profile does not have attendee")

    @staticmethod
    def details(current_user, attendee_id):

        return []

    @staticmethod
    def find_related_ones(
        current_user, target_attendee, querying_attendee_id, filters_list
    ):
        """
        return target_attendee's related ones, including dead ones, according to current_user permissions
        :param current_user:
        :param target_attendee:
        :param querying_attendee_id:
        :param filters_list:
        # :param priority: indicate what return result should sort by
        :return: related attendees of targeting attendee, or matched attendee depends on filter conditions and
                 current user permissions
        """

        if current_user and target_attendee:
            qs = (
                Attendee.objects
                if current_user.privileged
                else target_attendee.related_ones
            )
            if querying_attendee_id:
                return qs.filter(
                    pk=querying_attendee_id,
                    division__organization=current_user.organization,
                    is_removed=False,
                )
            else:
                if current_user.privileged:
                    init_query = Q(
                        division__organization=current_user.organization
                    ).add(  # preventing browser hacks since
                        Q(is_removed=False), Q.AND
                    )
                    final_query = init_query.add(
                        AttendeeService.filter_parser(filters_list, None, current_user),
                        Q.AND,
                    )
                    return qs.filter(final_query).order_by(
                        Case(
                            When(
                                id__in=target_attendee.related_ones.values_list(
                                    "id", flat=True
                                ),
                                then=0,
                            ),
                            default=1,
                        )
                    )  # https://stackoverflow.com/a/52047221/4257237
                else:
                    return qs
        else:
            return []

    @staticmethod
    def by_datagrid_params(
        current_user, meets, orderby_string, filters_list, include_dead
    ):
        """
        :param current_user:
        :param meets: attendee participated assembly ids. Exception: if assembly is in organization's
                      all_access_assemblies, all attendee of the same org will be return
        :param orderby_string:
        :param filters_list:
        :param include_dead:
        :return:
        """
        if not hasattr(current_user, 'attendee'):
            return []
        visitor_meet_id = current_user.organization.infos.get("settings", {}).get("default_visitor_meet")
        now = datetime.now(timezone.utc)
        orderby_list = AttendeeService.orderby_parser(
            orderby_string, meets, current_user
        )
        init_query_q = {
            "division__organization": current_user.organization,
            "is_removed": False,
            "folks__category": Attendee.FAMILY_CATEGORY,
        }
        if not include_dead:
            init_query_q["deathday__isnull"] = True

        init_query = Q(
            **init_query_q
        )  # Todo: need filter on attending_meet finish_date

        final_query = init_query.add(
            AttendeeService.filter_parser(filters_list, meets, current_user), Q.AND
        )
        qs = (
            Attendee.objects
            if current_user.can_see_all_organizational_meets_attendees()
            else current_user.attendee.scheduling_attendees()
        )
        return (
            qs.select_related()
            .prefetch_related()
            .annotate(
                attendingmeets=Coalesce(JSONBAgg(  # Coalesce required or null/true/false will break sorting
                    Func(
                        Value('attendingmeet_id'), 'attendings__attendingmeet',
                        Value('meet_slug'), 'attendings__meets__slug',
                        Value('attendingmeet_note'), 'attendings__attendingmeet__infos__note',
                        Value('attendingmeet_category'), 'attendings__attendingmeet__category',
                        function='jsonb_build_object',
                    ),
                    filter=Q(attendings__attendingmeet__finish__gte=now, attendings__attendingmeet__is_removed=False),
                    distinct=True,
                    default=[],
                ), Value('[]'), output_field=JSONField()),
                folkcities=Coalesce(JSONBAgg(  # Coalesce required or null/true/false will break sorting
                    Func(
                        Value('locality__name'), 'folks__places__address__locality__name',
                        Value('address__raw'), 'folks__places__address__raw',
                        Value('places__id'), 'folks__places__id',
                        function='jsonb_build_object',
                    ),
                    filter=(Q(folks__places__finish__isnull=True) | Q(folks__places__finish__gte=now)) & Q(folks__places__is_removed=False),
                    distinct=True,
                    default=[],
                ), Value('[]'), output_field=JSONField()),
                visitor_since=StringAgg(Substr(Cast('attendings__attendingmeet__start', CharField()), 1, 10),
                                        filter=Q(attendings__attendingmeet__meet=visitor_meet_id, attendings__attendingmeet__is_removed=False),
                                        delimiter=", ",
                                        distinct=True,
                                        default=None),
            ).filter(final_query).distinct()
            .order_by(*orderby_list)
        )

    @staticmethod
    def orderby_parser(orderby_string, meets, current_user):
        """
        generates sorter (column or OrderBy Func) based on user's choice
        :param orderby_string: JSON fetched from search params, will convert attendee.division to attendee__division
        :param meets: meet ids
        :param current_user:
        :return: a List of sorter for order_by()
        """
        meet_sorters = {  # this sorter only needed since there're dynamic columns (slug is column name)
            meet.slug: Func("attendingmeets", function="'[{\"meet_slug\":\"" + meet.slug + "\"}]'::jsonb <@ ")
            for meet in Meet.objects.filter(
                id__in=meets, assembly__division__organization=current_user.organization
            )
        }

        orderby_list = (
            []
        )  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]
        for orderby_dict in json.loads(orderby_string):
            field = orderby_dict.get("selector", "id").replace(".", "__")
            if field in meet_sorters:
                sorter = OrderBy(
                    meet_sorters[field], descending=orderby_dict.get("desc", False)
                )
                orderby_list.append(sorter)
            else:
                direction = "-" if orderby_dict.get("desc", False) else ""
                orderby_list.append(direction + field)
        return orderby_list

    @staticmethod
    def filter_parser(filters_list, meets, current_user):
        """
        A recursive method return Q function based on multi-level filter conditions. When filtering
        for attendingmeet, it adds extra filters on attendingmeet__finish gte conditions.
        :param filters_list: a string of multi-level list of filter conditions
        :param meets: optional meet ids
        :param current_user:
        :return: Q function, could be an empty Q()
        """
        and_string = Q.AND.lower()
        or_string = Q.OR.lower()

        if filters_list:
            if and_string in filters_list and or_string in filters_list:
                raise Exception(
                    "Can't process both 'or'/'and' at the same level! please wrap them in separated lists."
                )
            elif ('!' in filters_list and and_string in filters_list) or ('!' in filters_list and or_string in filters_list):
                raise Exception(
                    "Can't process 'or'/'and' with Unary filter(!) at the same level, please wrap them in separated lists."
                )
            elif '!' == filters_list[0]:   # currently only support one element for unary filter
                return ~AttendeeService.filter_parser(filters_list[1], meets, current_user)
            elif filters_list[1] == and_string:
                and_list = [
                    element for element in filters_list if element != and_string
                ]
                and_query = AttendeeService.filter_parser(
                    and_list[0], meets, current_user
                )
                for and_element in and_list[1:]:
                    and_query.add(
                        AttendeeService.filter_parser(and_element, meets, current_user),
                        Q.AND,
                    )
                return and_query
            elif filters_list[1] == or_string:
                or_list = [element for element in filters_list if element != or_string]
                or_query = AttendeeService.filter_parser(
                    or_list[0], meets, current_user
                )
                for or_element in or_list[1:]:
                    or_query.add(
                        AttendeeService.filter_parser(or_element, meets, current_user),
                        Q.OR,
                    )
                return or_query
            elif filters_list[1] == "=":
                condition = {
                    AttendeeService.field_convert(
                        filters_list[0], meets, current_user
                    ): filters_list[2],
                }
                if filters_list[0] == 'attendings__meets__slug' or (meets and Meet.objects.filter(id__in=meets, slug=filters_list[0], assembly__division__organization=current_user.organization).exists()):
                    condition['attendings__attendingmeet__finish__gte'] = datetime.now(timezone.utc)
                    condition['attendings__attendingmeet__is_removed'] = False

                return Q(**condition)
            elif filters_list[1] == "startswith":
                condition = {
                    AttendeeService.field_convert(
                        filters_list[0], meets, current_user
                    )
                    + "__istartswith": filters_list[2]
                }
                if meets and Meet.objects.filter(id__in=meets, slug=filters_list[0], assembly__division__organization=current_user.organization).exists():
                    condition['attendings__attendingmeet__finish__gte'] = datetime.now(timezone.utc)
                return Q(**condition)
            elif filters_list[1] == "endswith":
                condition = {
                    AttendeeService.field_convert(
                        filters_list[0], meets, current_user
                    )
                    + "__iendswith": filters_list[2]
                }
                if meets and Meet.objects.filter(id__in=meets, slug=filters_list[0], assembly__division__organization=current_user.organization).exists():
                    condition['attendings__attendingmeet__finish__gte'] = datetime.now(timezone.utc)
                return Q(**condition)
            elif filters_list[1] == "contains":
                condition = {
                    AttendeeService.field_convert(
                        filters_list[0], meets, current_user
                    )
                    + "__icontains": filters_list[2]
                }
                if meets and Meet.objects.filter(id__in=meets, slug=filters_list[0], assembly__division__organization=current_user.organization).exists():
                    condition['attendings__attendingmeet__finish__gte'] = datetime.now(timezone.utc)
                return Q(**condition)
            elif filters_list[1] == "notcontains":
                return ~Q(
                    **{
                        AttendeeService.field_convert(
                            filters_list[0], meets, current_user
                        )
                        + "__icontains": filters_list[2]
                    }
                )
            elif filters_list[1] == "<>":
                return ~Q(
                    **{
                        AttendeeService.field_convert(
                            filters_list[0], meets, current_user
                        ): filters_list[2]
                    }
                )
        return Q()

    @staticmethod
    def field_convert(query_field, meets, current_user):
        """
        some of the values are calculated cell values, and need to convert back to db field for search
        :return: string of fields in database
        """
        field_converter = {
            "self_phone_numbers": "infos__contacts",
            "self_email_addresses": "infos__contacts",
        }
        if meets:
            for meet in Meet.objects.filter(
                id__in=meets, assembly__division__organization=current_user.organization,
            ):
                field_converter[meet.slug] = "attendings__meets__display_name"

        return field_converter.get(query_field, query_field).replace(".", "__")

    @staticmethod
    def add_past(attendee, past_category_id, user_time_zone):
        category = Category.objects.get(pk=past_category_id)
        Past.objects.update_or_create(  # past does not have uniq key by natural
            organization=attendee.division.organization,
            content_type=ContentType.objects.get_for_model(attendee),
            object_id=attendee.id,
            category=category,
            when=PartialDate(datetime.now(user_time_zone).strftime('%Y-%m-%d')),
            display_name=f'become {category.display_name}',
            infos=Utility.relationship_infos(),
        )

    @staticmethod
    def end_all_activities(attendee, updating_attendee_uuid_str):
        """FamilyAttendee is not deleted since many people still memorise their passed away families"""
        for attending in attendee.attendings.all():
            AttendingService.end_all_activities(attending)

        now = datetime.now(timezone.utc)
        attendee.pasts.filter(Q(finish__isnull=True) | Q(finish__gte=now)).update(
            finish=now
        )
        attendee.places.filter(Q(finish__isnull=True) | Q(finish__gte=now)).update(
            finish=now
        )

        for family in attendee.families.filter(is_removed=False):
            if (
                family.folkattendee_set.filter(
                    (Q(finish__isnull=True) | Q(finish__gte=now)),
                    attendee__deathday__isnull=True,
                    is_removed=False,
                    attendee__is_removed=False,
                ).count()
                < 1
            ):  # single household family (after attendee's deathday updated)
                family.places.filter(
                    Q(finish__isnull=True) | Q(finish__gte=now)
                ).update(finish=now)

        attendee_id = str(attendee.id)
        for scheduler in Attendee.objects.filter(infos__schedulers__contains={attendee_id: True}):
            scheduler.infos['schedulers'][attendee_id] = False
            scheduler.infos['updating_attendees'][updating_attendee_uuid_str] = Utility.now_with_timezone().isoformat(timespec='minutes')
            scheduler.save()

        for contact in Attendee.objects.filter(infos__emergency_contacts__contains={attendee_id: True}):
            contact.infos['emergency_contacts'][attendee_id] = False
            contact.infos['updating_attendees'][updating_attendee_uuid_str] = Utility.now_with_timezone().isoformat(timespec='minutes')
            contact.save()

        attendee_user = attendee.user
        if attendee_user:
            attendee_user.is_active = False
            attendee_user.save()

    @staticmethod
    def destroy_with_associations(attendee):
        for attending in attendee.attendings.filter(is_removed=False):
            AttendingService.destroy_with_associations(attending)

        attendee.pasts.filter(is_removed=False).delete()

        # Relationship.objects.filter(
        #     (Q(from_attendee=attendee)
        #      |
        #      Q(to_attendee=attendee)),
        #     is_removed=False,
        # ).delete()

        for place in attendee.places.filter(is_removed=False):
            PlaceService.destroy_with_associations(place)

        for family in attendee.folks.filter(is_removed=False):
            FolkService.destroy_with_associations(family, attendee)

        for registration in Registration.objects.filter(
            registrant=attendee, is_removed=False
        ):
            registration.registrant = None
            if not registration.attending_set.filter(is_removed=False):
                registration.delete()
            else:
                registration.save()

        old_photo = attendee.photo
        if (
            old_photo
        ):  # Todo 20211102: may need to search photos of attendee name due to repeating import
            old_file = Path(old_photo.path)
            old_file.unlink(missing_ok=True)

        attendee_user = attendee.user
        if attendee_user:
            attendee.delete()
            attendee_user.delete()
        else:
            attendee.delete()
        # Todo 20211102: CCPA deletion requires history removal too

    @staticmethod
    def create_or_update_first_folk(attendee, folk_name, category_id, role_id, print_directory=False):
        potential_non_family_folk = attendee.folks.filter(category=category_id).first()
        folk, folk_created = Folk.objects.update_or_create(
            id=potential_non_family_folk.id if potential_non_family_folk else None,
            defaults={
                "division": attendee.division,
                "category": Category.objects.get(pk=category_id),
                "display_name": folk_name,
                "infos": {"print_directory": print_directory},
            },
        )
        FolkAttendee.objects.update_or_create(
            folk=folk,
            attendee=attendee,
            defaults={
                "folk": folk,
                "attendee": attendee,
                "role": Relation.objects.get(pk=role_id),
            },
        )
        return folk

    @staticmethod
    def get_roster_data(organization, meet_slugs, start, finish, skip, take, sort_list=None, search_value=None):
        if not sort_list:
            sort_list = ['first_name', 'last_name']

        # 1. Query Gatherings (Columns)
        gatherings = Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization=organization,
            start__gte=start,
            finish__lte=finish,
            is_removed=False
        ).order_by('start', 'meet__display_name', 'id')

        from attendees.occasions.services import GatheringService

        gathering_list = GatheringService.get_roster_gatherings(
            organization=organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
        )

        # 2. Query Attendees (Rows) with Database Aggregation
        attendingmeet_filter = (
            Q(attendings__attendingmeet__meet__slug__in=meet_slugs) &
            Q(attendings__attendingmeet__is_removed=False) &
            Q(attendings__is_removed=False) &
            (Q(attendings__attendingmeet__finish__isnull=True) | Q(attendings__attendingmeet__finish__gte=start)) &
            (Q(attendings__attendingmeet__start__isnull=True) | Q(attendings__attendingmeet__start__lte=finish))
        )

        attendees_qs = Attendee.objects.filter(
            attendingmeet_filter,
            is_removed=False
        )

        if search_value:
            search_filter = (
                Q(first_name__icontains=search_value) |
                Q(last_name__icontains=search_value) |
                Q(first_name2__icontains=search_value) |
                Q(last_name2__icontains=search_value) |
                Q(infos__names__original__icontains=search_value) |
                Q(infos__contacts__icontains=search_value) |
                Q(infos__icontains=search_value) |
                Q(attendings__attendingmeet__team__display_name__icontains=search_value) |
                Q(attendings__attendingmeet__character__display_name__icontains=search_value)
            )
            attendees_qs = attendees_qs.filter(search_filter)

        normalized_sort_list = []
        for s in sort_list:
            if s.startswith('-attendee__'):
                normalized_sort_list.append('-' + s[11:])
            elif s.startswith('attendee__'):
                normalized_sort_list.append(s[10:])
            elif s in ('team__display_order', 'team__display_name', 'team'):
                normalized_sort_list.append(F('team__display_order').asc(nulls_last=True))
                normalized_sort_list.append('team__display_name')
            elif s in ('-team__display_order', '-team__display_name', '-team'):
                normalized_sort_list.append(F('team__display_order').desc(nulls_last=True))
                normalized_sort_list.append('-team__display_name')
            elif s in ('character__display_name', 'character'):
                normalized_sort_list.append('character__display_name')
            elif s in ('-character__display_name', '-character'):
                normalized_sort_list.append('-character__display_name')
            else:
                normalized_sort_list.append(s)

        attendees_qs = attendees_qs.annotate(
            team__display_name=StringAgg(
                'attendings__attendingmeet__team__display_name',
                delimiter=', ',
                distinct=True,
                filter=attendingmeet_filter,
                default=None,
            ),
            team__display_order=Min(
                'attendings__attendingmeet__team__display_order',
                filter=attendingmeet_filter,
            ),
            character__display_name=StringAgg(
                'attendings__attendingmeet__character__display_name',
                delimiter=', ',
                distinct=True,
                filter=attendingmeet_filter,
                default=None,
            ),
            total_attendances=Count(
                'attendings__attendance',
                filter=Q(
                    attendings__attendance__gathering__in=gatherings,
                    attendings__attendance__is_removed=False
                ) & ~Q(attendings__attendance__category_id=1),
                distinct=True
            ),
            attendances=Coalesce(JSONBAgg(
                Func(
                    Value('attendance_id'), 'attendings__attendance__id',
                    Value('attending_id'), 'attendings__attendance__attending__id',
                    Value('category_id'), 'attendings__attendance__category__id',
                    Value('category_name'), 'attendings__attendance__category__display_name',
                    Value('gathering_id'), 'attendings__attendance__gathering__id',
                    Value('start'), 'attendings__attendance__start',
                    Value('finish'), 'attendings__attendance__finish',
                    Value('file_path'), 'attendings__attendance__file',
                    function='jsonb_build_object',
                ),
                filter=Q(attendings__attendance__gathering__in=gatherings, attendings__attendance__is_removed=False),
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
            attendingmeets=Coalesce(JSONBAgg(
                Func(
                    Value('attending_id'), 'attendings__attendingmeet__attending_id',
                    Value('attendingmeet_id'), 'attendings__attendingmeet__id',
                    Value('meet_id'), 'attendings__attendingmeet__meet_id',
                    Value('meet_name'), 'attendings__attendingmeet__meet__display_name',
                    Value('character_id'), 'attendings__attendingmeet__character_id',
                    Value('character_name'), 'attendings__attendingmeet__character__display_name',
                    Value('team_id'), 'attendings__attendingmeet__team_id',
                    Value('team_name'), 'attendings__attendingmeet__team__display_name',
                    Value('start'), 'attendings__attendingmeet__start',
                    Value('finish'), 'attendings__attendingmeet__finish',
                    Value('infos'), 'attendings__attendingmeet__infos',
                    function='jsonb_build_object',
                ),
                filter=attendingmeet_filter,
                distinct=True,
                default=[],
            ), Value('[]'), output_field=JSONField()),
        ).distinct().order_by(*normalized_sort_list)

        total_count = attendees_qs.count()
        attendees_page = attendees_qs[skip: skip + take]

        # 3. Build Response
        rows = []
        for attendee in attendees_page:
            photo_url = None
            if attendee.photo:
                try:
                    photo_url = attendee.photo.url
                except ValueError:
                    pass

            primary_attending_id = attendee.attendingmeets[0]['attending_id'] if attendee.attendingmeets else None

            contacts_dict = attendee.infos.get('contacts', {}) if isinstance(attendee.infos, dict) else {}
            contacts_parts = []
            if isinstance(contacts_dict, dict):
                for k, v in contacts_dict.items():
                    if v:
                        contacts_parts.append(str(v))
            contacts_str = ", ".join(contacts_parts)

            rows.append({
                "attending_id": primary_attending_id,
                "attendee_id": attendee.id,
                "attendee_name": attendee.display_label,
                "photo_url": photo_url,
                "team__display_name": attendee.team__display_name,
                "team__display_order": attendee.team__display_order,
                "character__display_name": attendee.character__display_name,
                "contacts": contacts_str,
                "attendances": attendee.attendances,
                "attendingmeets": attendee.attendingmeets,
                "total_attendances": attendee.total_attendances,
            })

        return gathering_list, rows, total_count

    @staticmethod
    def search_for_roster(current_user, meet_slug, query):
        """
        Omni search for attendees to be added or checked into a roster.
        - Validates that current_user has an organization and that meet belongs to current_user.organization.
        - If current_user.can_see_all_organizational_meets_attendees() is True, searches across organization.
        - If False, restricts search to attendees sharing a Folk with current_user.attendee.
        - Supports phone search (last 4 digits or formatted), multi-word names, traditional/simplified Chinese
          (via OpenCC), romanization (via unidecode), and fuzzy typo matching (via pg_trgm TrigramSimilarity).
        - If meet.infos['kid_search_families_show_grades'] is True:
            - Performs cross-relation search: includes other members sharing a Folk with matched attendees.
            - Includes age, grade_name (mapped via organization.infos['grade_converter']), grade_index, and guardians.
        - Phone masking: first phone displays only last 2 digits (***-**99).
        - Returns complete folks array for each candidate.
        - Identifies meet_status ('paused', 'enrolled', 'expired', 'not_enrolled') and can_join boolean.
          PAUSED status CANNOT be auto-joined (can_join=False).
        """
        if not current_user or not current_user.is_authenticated or not getattr(current_user, "organization", None):
            raise PermissionDenied("Authentication and organization are required.")

        if not meet_slug:
            raise ValueError("meet_slug is required.")

        meet = (
            Meet.objects.filter(slug=meet_slug, is_removed=False)
            .select_related("assembly__division__organization")
            .first()
        )
        if not meet:
            raise Http404("Meet not found.")

        meet_org = (
            meet.assembly.division.organization
            if (meet.assembly and meet.assembly.division)
            else None
        )
        if not meet_org or meet_org.id != current_user.organization.id:
            raise PermissionDenied("User does not have access to this meet's organization.")

        q = (query or "").strip()
        if not q:
            return []

        can_see_all = current_user.can_see_all_organizational_meets_attendees()
        user_folk_ids = None

        if can_see_all:
            base_qs = Attendee.objects.filter(
                division__organization=current_user.organization,
                is_removed=False,
            )
        else:
            if not hasattr(current_user, "attendee") or not current_user.attendee:
                return []
            user_folk_ids = list(
                current_user.attendee.folks.filter(is_removed=False).values_list("id", flat=True)
            )
            base_qs = Attendee.objects.filter(
                folks__in=user_folk_ids,
                division__organization=current_user.organization,
                is_removed=False,
            ).distinct()

        # Annotate contacts as string for regex matching on JSON values
        base_qs = base_qs.annotate(contacts_str=Cast("infos__contacts", CharField()))

        # Match query directly against precomputed database fields
        match_q = (
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(first_name2__icontains=q)
            | Q(last_name2__icontains=q)
            | Q(infos__names__original__icontains=q)
            | Q(infos__names__traditional__icontains=q)
            | Q(infos__names__simplified__icontains=q)
            | Q(infos__names__romanization__icontains=q)
            | Q(infos__names__nick__icontains=q)
            | Q(contacts_str__iregex=r':\s*\"[^\"]*' + re.escape(q))
        )

        # Multi-word matching (e.g. "Daniel Bo" or "Hannah 傅")
        words = [w for w in q.split() if len(w) > 0]
        if len(words) > 1:
            multi_word_q = Q()
            for w in words:
                multi_word_q &= (
                    Q(first_name__icontains=w)
                    | Q(last_name__icontains=w)
                    | Q(first_name2__icontains=w)
                    | Q(last_name2__icontains=w)
                    | Q(infos__names__original__icontains=w)
                    | Q(infos__names__traditional__icontains=w)
                    | Q(infos__names__simplified__icontains=w)
                    | Q(infos__names__romanization__icontains=w)
                    | Q(infos__names__nick__icontains=w)
                )
            match_q |= multi_word_q

        # Phone matching: last 4 digits or full phone number across any phone1, phone2, phone3...
        digits = re.sub(r"\D", "", q)
        if len(digits) >= 4:
            phone_pattern = r':\s*\"[^\"]*' + r'\D*'.join(digits[-10:]) + r'\D*\"'
            match_q |= Q(contacts_str__regex=phone_pattern)

        # Fuzzy matching using pg_trgm TrigramSimilarity against DB precomputed fields if length >= 3
        has_sim = False
        direct_attendees = []
        if len(q) >= 3:
            try:
                from django.contrib.postgres.search import TrigramSimilarity
                from django.db.models.functions import Greatest

                sim_expr = Greatest(
                    TrigramSimilarity(Cast("infos__names__original", CharField()), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__traditional", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__simplified", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__romanization", CharField()), Value("")), q),
                    TrigramSimilarity(Coalesce(Cast("infos__names__nick", CharField()), Value("")), q),
                    TrigramSimilarity("first_name", q),
                    TrigramSimilarity("last_name", q),
                    TrigramSimilarity(Coalesce("first_name2", Value("")), q),
                    TrigramSimilarity(Coalesce("last_name2", Value("")), q),
                )
                direct_qs = (
                    base_qs.annotate(similarity=sim_expr)
                    .filter(match_q | Q(similarity__gte=0.25))
                    .order_by("-similarity", "last_name", "first_name")
                )
                direct_attendees = list(direct_qs[:25])
                has_sim = True
            except Exception:
                has_sim = False

        if not has_sim:
            direct_qs = base_qs.filter(match_q).order_by("last_name", "first_name")
            direct_attendees = list(direct_qs[:25])

        is_kid_meet = bool(meet.infos.get("kid_search_families_show_grades")) if meet.infos else False

        # Build candidate map: attendee_id -> { 'attendee': attendee, 'matched_by': ..., 'relation_source_name': ... }
        candidates_map = {}
        for a in direct_attendees:
            candidates_map[a.id] = {
                "attendee": a,
                "matched_by": "direct",
                "relation_source_name": None,
            }

        # Cross-relation search if kid_search_families_show_grades is True
        if is_kid_meet and direct_attendees:
            direct_ids = [a.id for a in direct_attendees]
            fa_qs = FolkAttendee.objects.filter(
                attendee_id__in=direct_ids,
                is_removed=False,
                folk__is_removed=False,
            ).values("folk_id", "attendee_id")

            folk_to_direct_attendees = {}
            for item in fa_qs:
                folk_to_direct_attendees.setdefault(item["folk_id"], []).append(item["attendee_id"])

            if folk_to_direct_attendees:
                related_fa_qs = FolkAttendee.objects.filter(
                    folk_id__in=folk_to_direct_attendees.keys(),
                    is_removed=False,
                    folk__is_removed=False,
                ).exclude(
                    attendee_id__in=direct_ids
                ).values("attendee_id", "folk_id")

                related_attendee_folk_map = {}
                for item in related_fa_qs:
                    related_attendee_folk_map[item["attendee_id"]] = item["folk_id"]

                if related_attendee_folk_map:
                    rel_attendees_qs = Attendee.objects.filter(
                        id__in=related_attendee_folk_map.keys(),
                        division__organization=current_user.organization,
                        is_removed=False,
                    )
                    if not can_see_all and user_folk_ids:
                        rel_attendees_qs = rel_attendees_qs.filter(folks__in=user_folk_ids).distinct()

                    direct_attendee_lookup = {a.id: a for a in direct_attendees}
                    for rel_attendee in rel_attendees_qs[:25]:
                        if rel_attendee.id not in candidates_map:
                            f_id = related_attendee_folk_map.get(rel_attendee.id)
                            source_ids = folk_to_direct_attendees.get(f_id, [])
                            source_name = None
                            if source_ids and source_ids[0] in direct_attendee_lookup:
                                source_name = direct_attendee_lookup[source_ids[0]].display_label
                            candidates_map[rel_attendee.id] = {
                                "attendee": rel_attendee,
                                "matched_by": "relation",
                                "relation_source_name": source_name,
                            }

        if not candidates_map:
            return []

        all_candidate_ids = list(candidates_map.keys())[:35]
        now_dt = datetime.now(timezone.utc)

        # Batch query AttendingMeets for target meet
        ams = (
            AttendingMeet.objects.filter(
                attending__attendee_id__in=all_candidate_ids,
                meet=meet,
                is_removed=False,
            )
            .select_related("attending", "category")
            .order_by("-finish", "-created")
        )
        ams_by_attendee = {}
        for am in ams:
            ams_by_attendee.setdefault(am.attending.attendee_id, []).append(am)

        # Batch query latest active Attending
        latest_attendings = (
            Attending.objects.filter(
                attendee_id__in=all_candidate_ids,
                is_removed=False,
            )
            .order_by("attendee_id", "-created")
        )
        attending_by_attendee = {}
        for att in latest_attendings:
            if att.attendee_id not in attending_by_attendee:
                attending_by_attendee[att.attendee_id] = att.id

        # Batch query FolkAttendee for all candidates to build folks array
        all_fas = (
            FolkAttendee.objects.filter(
                attendee_id__in=all_candidate_ids,
                is_removed=False,
                folk__is_removed=False,
            )
            .select_related("folk", "folk__category", "role")
            .order_by("display_order", "id")
        )
        fas_by_attendee = {}
        for fa in all_fas:
            fas_by_attendee.setdefault(fa.attendee_id, []).append(fa)

        grade_converter = (
            current_user.organization.infos.get("grade_converter", [])
            if (current_user.organization and isinstance(current_user.organization.infos, dict))
            else []
        )

        results = []
        for cand_id in all_candidate_ids:
            cand_info = candidates_map[cand_id]
            attendee = cand_info["attendee"]

            # AttendingMeet status
            cand_ams = ams_by_attendee.get(attendee.id, [])
            if any(am.category_id == Attendee.PAUSED_CATEGORY for am in cand_ams):
                meet_status = "paused"
                can_join = False
                matched_am = next(am for am in cand_ams if am.category_id == Attendee.PAUSED_CATEGORY)
                am_id = matched_am.id
            elif any(am.finish is None or am.finish >= now_dt for am in cand_ams):
                meet_status = "enrolled"
                can_join = False
                matched_am = next(am for am in cand_ams if am.finish is None or am.finish >= now_dt)
                am_id = matched_am.id
            elif cand_ams:
                meet_status = "expired"
                can_join = True
                am_id = cand_ams[0].id
            else:
                meet_status = "not_enrolled"
                can_join = True
                am_id = None

            # Photo URL
            photo_url = None
            if attendee.photo:
                try:
                    photo_url = attendee.photo.url
                except Exception:
                    pass

            # Masked phone (last 2 digits of first phone)
            contacts = attendee.infos.get("contacts", {}) if isinstance(attendee.infos, dict) else {}
            phone_val = None
            if isinstance(contacts, dict):
                phone_val = contacts.get("phone1")
                if not phone_val:
                    for k, v in contacts.items():
                        if "phone" in k.lower() and v:
                            phone_val = str(v)
                            break
            masked_phone = None
            if phone_val:
                p_digits = re.sub(r"\D", "", str(phone_val))
                if len(p_digits) >= 2:
                    masked_phone = f"***-**{p_digits[-2:]}"
                else:
                    masked_phone = "***"

            # Age, grade, and guardians
            if is_kid_meet:
                age = attendee.age()
                grade_idx = (
                    attendee.infos.get("fixed", {}).get("grade")
                    if isinstance(attendee.infos, dict)
                    else None
                )
                grade_name = None
                grade_index = None
                if grade_idx is not None:
                    try:
                        g_int = int(grade_idx)
                        if 0 <= g_int < len(grade_converter):
                            grade_name = grade_converter[g_int]
                        else:
                            grade_name = str(g_int)
                        grade_index = g_int
                    except (ValueError, TypeError):
                        grade_name = str(grade_idx)

                guardians = attendee.parents_notifiers_names
                if not guardians:
                    family_fas = fas_by_attendee.get(attendee.id, [])
                    fam_folk_ids = [fa.folk_id for fa in family_fas if fa.folk.category_id == Attendee.FAMILY_CATEGORY]
                    if fam_folk_ids:
                        fam_members = Attendee.objects.filter(
                            folks__in=fam_folk_ids,
                            division__organization=current_user.organization,
                            is_removed=False,
                        ).exclude(id=attendee.id).distinct()
                        adult_guardians = [m.display_label for m in fam_members if (m.age() is None or m.age() >= 18)]
                        guardians = ", ".join(adult_guardians) if adult_guardians else None
            else:
                age = None
                grade_name = None
                grade_index = None
                guardians = None

            # Full folks array
            cand_fas = fas_by_attendee.get(attendee.id, [])
            folks_list = [
                {
                    "id": str(fa.folk.id),
                    "name": fa.folk.display_name or "",
                    "category_id": fa.folk.category_id,
                    "category_name": fa.folk.category.display_name if fa.folk.category else "",
                    "role_id": fa.role_id,
                    "role_title": fa.role.title if fa.role else "",
                    "is_emergency_contact": fa.role.emergency_contact if fa.role else False,
                    "display_order": fa.display_order,
                }
                for fa in cand_fas
            ]

            results.append({
                "id": str(attendee.id),
                "name": attendee.display_label,
                "first_name": attendee.first_name or "",
                "last_name": attendee.last_name or "",
                "first_name2": attendee.first_name2 or "",
                "last_name2": attendee.last_name2 or "",
                "gender": attendee.gender,
                "actual_birthday": attendee.actual_birthday.isoformat() if attendee.actual_birthday else None,
                "estimated_birthday": str(attendee.estimated_birthday) if attendee.estimated_birthday else None,
                "photo_url": photo_url,
                "masked_phone": masked_phone,
                "age": age,
                "grade_name": grade_name,
                "grade_index": grade_index,
                "guardians": guardians,
                "meet_status": meet_status,
                "can_join": can_join,
                "attendingmeet_id": am_id,
                "attending_id": attending_by_attendee.get(attendee.id),
                "folks": folks_list,
                "matched_by": cand_info["matched_by"],
                "relation_source_name": cand_info["relation_source_name"],
            })

        return results

    @staticmethod
    def get_g12_index(grade_converter):
        """
        Locates the 0-based index for G12 in grade_converter list.
        Returns None if not found.
        """
        if not grade_converter or not isinstance(grade_converter, list):
            return None
        for idx, item in enumerate(grade_converter):
            norm = str(item).strip().upper().replace(" ", "").replace("-", "")
            if norm in ("G12", "GRADE12", "12THGRADE"):
                return idx
        return None

    @staticmethod
    def advance_grades(organization_infos=None, organization_slug=None, dry_run=False):
        """
        Advances the school grade of all active attendees in organizations that have
        infos['grade_converter'] or infos['settings']['grade_converter'].
        - Skips organizations without grade_converter or with an empty list.
        - Uses grade_converter as the grade progression source and activation flag.
        - Strictly caps advancement at G12: students already at or past G12 are NOT incremented.
        - Preserves and logs pghistory snapshot.
        - Returns a structured dictionary of results for Celery logs and admin commands.
        """
        from attendees.whereabouts.models import Organization

        org_qs = Organization.objects.filter(is_removed=False)
        if organization_infos and isinstance(organization_infos, list):
            slugs = [
                item.get("organization_slug") or item.get("slug")
                for item in organization_infos
                if isinstance(item, dict) and (item.get("organization_slug") or item.get("slug"))
            ]
            if slugs:
                org_qs = org_qs.filter(slug__in=slugs)
        elif organization_slug:
            if isinstance(organization_slug, int) or (isinstance(organization_slug, str) and organization_slug.isdigit()):
                org_qs = org_qs.filter(id=int(organization_slug))
            else:
                org_qs = org_qs.filter(slug=organization_slug)

        total_updated = 0
        total_capped = 0
        orgs_processed = 0
        orgs_skipped = 0
        org_summaries = []

        with pghistory.context(modifier="advance grades"):
            for org in org_qs:
                raw_converter = (
                    (org.infos.get("settings") or {}).get("grade_converter")
                    or org.infos.get("grade_converter")
                ) if isinstance(org.infos, dict) else None
                if not raw_converter or not isinstance(raw_converter, list) or len(raw_converter) == 0:
                    orgs_skipped += 1
                    org_summaries.append({
                        "id": org.id,
                        "slug": org.slug,
                        "name": org.display_name,
                        "status": "skipped",
                        "reason": "No grade_converter configured in organization.infos",
                        "updated_count": 0,
                        "capped_count": 0,
                        "students": [],
                    })
                    continue

                g12_idx = AttendeeService.get_g12_index(raw_converter)
                org_updated = 0
                org_capped = 0
                student_details = []

                attendees_qs = Attendee.objects.filter(
                    division__organization=org,
                    is_removed=False,
                    merged_into__isnull=True,
                    deathday__isnull=True,
                    infos__fixed__grade__isnull=False,
                ).order_by("created")

                atomic_ctx = transaction.atomic() if not dry_run else nullcontext()
                with atomic_ctx:
                    for attendee in attendees_qs:
                        if not isinstance(attendee.infos, dict):
                            continue
                        fixed = attendee.infos.get("fixed", {})
                        if not isinstance(fixed, dict):
                            continue

                        raw_grade = fixed.get("grade")
                        if raw_grade is None:
                            continue

                        current_grade = None
                        if isinstance(raw_grade, (int, float)):
                            current_grade = int(raw_grade)
                        elif isinstance(raw_grade, str):
                            if raw_grade in raw_converter:
                                current_grade = raw_converter.index(raw_grade)
                            elif raw_grade.isdigit() or (raw_grade.startswith("-") and raw_grade[1:].isdigit()):
                                current_grade = int(raw_grade)

                        if current_grade is None:
                            continue

                        # Check if capped at or past G12
                        if g12_idx is not None and current_grade >= g12_idx:
                            org_capped += 1
                            continue
                        elif current_grade >= len(raw_converter) - 1:
                            org_capped += 1
                            continue

                        new_grade = current_grade + 1
                        old_grade_name = raw_converter[current_grade] if 0 <= current_grade < len(raw_converter) else str(current_grade)
                        new_grade_name = raw_converter[new_grade] if 0 <= new_grade < len(raw_converter) else str(new_grade)

                        student_details.append({
                            "attendee_id": str(attendee.id),
                            "name": attendee.display_label,
                            "old_grade": current_grade,
                            "old_grade_name": old_grade_name,
                            "new_grade": new_grade,
                            "new_grade_name": new_grade_name,
                        })

                        if not dry_run:
                            fixed["grade"] = new_grade
                            if "school_grade" in fixed and isinstance(fixed["school_grade"], int):
                                if fixed["school_grade"] < 12:
                                    fixed["school_grade"] += 1
                            attendee.infos["fixed"] = fixed
                            attendee.save(update_fields=["infos"])

                        org_updated += 1

                orgs_processed += 1
                total_updated += org_updated
                total_capped += org_capped
                org_summaries.append({
                    "id": org.id,
                    "slug": org.slug,
                    "name": org.display_name,
                    "status": "processed",
                    "reason": None,
                    "updated_count": org_updated,
                    "capped_count": org_capped,
                    "students": student_details,
                })

        return {
            "total_organizations": org_qs.count(),
            "organizations_processed": orgs_processed,
            "organizations_skipped": orgs_skipped,
            "total_updated": total_updated,
            "total_capped": total_capped,
            "organizations": org_summaries,
        }

    @staticmethod
    def normalize_phone_number(val):
        if not val or not isinstance(val, str):
            return val
        trimmed = val.strip()
        if not trimmed:
            return trimmed
        digits = re.sub(r"\D", "", trimmed)
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if trimmed.startswith("+") and len(digits) >= 7:
            return f"+{digits}"
        if len(digits) >= 10:
            return f"+1{digits[-10:]}"
        return trimmed

    @staticmethod
    def fast_onboard(
        current_user,
        meet_slug,
        attendees_data=None,
        companions=None,
        unaccompanied=False,
        gathering_id=None,
        kid_data=None,
        parent_data=None,
    ):
        """
        Fast onboard one or more attendees (and optional companions) into a meet.
        - Validates current_user organization permissions.
        - Reads meet.assembly.division.infos["show_attendee_infos"] to check if kid meet.
        - Enforces strict Birthday rules:
            - Never asks for age; accepts birthday_year, birthday_month, birthday_day.
            - Birthday year cannot exceed current year or be before 1900.
            - Birthday cannot be in the future.
            - If kid meet (infos-grade is true):
                - All 3 parts required, stored in actual_birthday (YYYY-MM-DD).
                - Grade and food_pref (allergies) are mandatory.
                - Insurer optional if infos-insurer is true.
            - If adult meet:
                - If Y/M/D complete: actual_birthday.
                - If partial (missing year): stored in estimated_birthday as '1800-MM-DD'.
                - If partial (missing day/month): stored in estimated_birthday as 'YYYY' or 'YYYY-MM'.
        - Companion handling:
            - If unaccompanied: sets attendingmeet.infos['special'] = {'check_in': '⚠Missing companion info'}.
            - In kid meets: companion contact required unless unaccompanied.
            - In adult meets: companion contact is optional (only name required).
            - Folk & FolkAttendee creation:
                - If kid meet: kids get role son/daughter/child (rank 11 + idx), companions get rank 1 (parent or specified relation).
                - If adult meet: role is assigned based on gender (male -> husband rank 1, female -> wife rank 2, unspecified -> spouse rank 1/2).
        - Enrolls all attendees in meet (AttendingMeet) and optionally records Attendance for gathering_id.
        """
        if not current_user or not current_user.is_authenticated or not getattr(current_user, "organization", None):
            raise PermissionDenied("Authentication and organization are required.")

        if not meet_slug:
            raise ValidationError({"meet_slug": "meet_slug is required."})

        # Backward compatibility for kid_data and parent_data
        if attendees_data is None and kid_data is not None:
            attendees_data = kid_data

        if isinstance(attendees_data, dict):
            attendees_data = [attendees_data]
        elif not isinstance(attendees_data, list):
            attendees_data = []

        if not attendees_data:
            raise ValidationError({"attendees_data": "attendees_data list is required."})

        companions_raw = companions
        if not companions_raw and parent_data:
            companions_raw = [parent_data] if isinstance(parent_data, dict) else parent_data
        companions = companions_raw if isinstance(companions_raw, list) else []

        meet = (
            Meet.objects.filter(slug=meet_slug, is_removed=False)
            .select_related("assembly__division__organization", "major_character")
            .first()
        )
        if not meet:
            raise Http404("Meet not found.")

        meet_org = (
            meet.assembly.division.organization
            if (meet.assembly and meet.assembly.division)
            else None
        )
        if not meet_org or meet_org.id != current_user.organization.id:
            raise PermissionDenied("User does not have access to this meet's organization.")

        show_attendee_infos = (
            meet.assembly.division.infos.get("show_attendee_infos", {})
            if (meet.assembly and meet.assembly.division and meet.assembly.division.infos)
            else {}
        )
        is_kid_meet = bool(show_attendee_infos.get("infos-grade") or show_attendee_infos.get("grade"))
        show_insurer = bool(show_attendee_infos.get("infos-insurer") or show_attendee_infos.get("insurer"))

        # 1. Validate all attendees data
        now_date = date.today()
        current_year = now_date.year
        validated_attendees = []

        for idx, att_data in enumerate(attendees_data):
            att_label = f"Attendee {idx + 1}" if len(attendees_data) > 1 else "Attendee"
            first_name = (att_data.get("first_name") or "").strip() or None
            last_name = (att_data.get("last_name") or "").strip() or None
            first_name2 = (att_data.get("first_name2") or "").strip() or None
            last_name2 = (att_data.get("last_name2") or "").strip() or None
            if not (first_name or last_name or first_name2 or last_name2):
                raise ValidationError({"name": f"{att_label} name (English or other language) is required."})

            gender = att_data.get("gender") or GenderEnum.UNSPECIFIED.value

            byear = att_data.get("birthday_year")
            bmonth = att_data.get("birthday_month")
            bday = att_data.get("birthday_day")
            try:
                byear = int(byear) if byear is not None and str(byear).strip() != "" else None
                bmonth = int(bmonth) if bmonth is not None and str(bmonth).strip() != "" else None
                bday = int(bday) if bday is not None and str(bday).strip() != "" else None
            except (ValueError, TypeError):
                raise ValidationError({"birthday": f"{att_label} birthday year, month, and day must be valid numbers."})

            if byear is not None:
                if byear > current_year:
                    raise ValidationError({"birthday": f"Birth year cannot exceed {current_year}."})
                if byear < 1900:
                    raise ValidationError({"birthday": "Birth year must be 1900 or later."})

            actual_birthday = None
            estimated_birthday = None

            if is_kid_meet:
                if not (byear and bmonth and bday):
                    raise ValidationError({"birthday": "Year, Month, and Day of birth are required for kids."})
                try:
                    actual_birthday = date(byear, bmonth, bday)
                except ValueError as e:
                    raise ValidationError({"birthday": f"Invalid birthday date: {e}"})

                if actual_birthday > now_date:
                    raise ValidationError({"birthday": "Birthday cannot be in the future."})

                grade = att_data.get("grade")
                if grade is None or str(grade).strip() == "":
                    raise ValidationError({"grade": "School grade is required for kids."})

                food_pref = (att_data.get("food_pref") or "").strip()
                if not food_pref:
                    raise ValidationError({"food_pref": "Food preference / allergies is required for kids (enter 'None' if none)."})

                insurer = (att_data.get("insurer") or "").strip() if show_insurer else None
            else:
                if byear and bmonth and bday:
                    try:
                        actual_birthday = date(byear, bmonth, bday)
                    except ValueError as e:
                        raise ValidationError({"birthday": f"Invalid birthday date: {e}"})
                    if actual_birthday > now_date:
                        raise ValidationError({"birthday": "Birthday cannot be in the future."})
                elif bmonth and bday and not byear:
                    estimated_birthday = f"1800-{bmonth:02d}-{bday:02d}"
                elif byear and bmonth:
                    estimated_birthday = f"{byear:04d}-{bmonth:02d}"
                elif byear:
                    estimated_birthday = f"{byear:04d}"

                grade = att_data.get("grade")
                food_pref = (att_data.get("food_pref") or "").strip() or None
                insurer = (att_data.get("insurer") or "").strip() if show_insurer else None

            fixed = {}
            if grade is not None and str(grade).strip() != "":
                try:
                    fixed["grade"] = int(grade)
                except (ValueError, TypeError):
                    fixed["grade"] = grade
            if food_pref:
                fixed["food_pref"] = food_pref
            if insurer:
                fixed["insurer"] = insurer

            contacts = {}
            raw_contacts = att_data.get("contacts")
            if isinstance(raw_contacts, list):
                type_counts = {}
                for c in raw_contacts:
                    ct = (c.get("type") or "phone").strip().lower()
                    cv = (c.get("value") or "").strip()
                    if cv:
                        if ct in ("phone", "whatsapp"):
                            cv = AttendeeService.normalize_phone_number(cv)
                        type_counts[ct] = type_counts.get(ct, 0) + 1
                        c_idx = type_counts[ct]
                        contacts[f"{ct}{c_idx}"] = cv
                        if c_idx == 1:
                            contacts[ct] = cv
            elif isinstance(raw_contacts, dict):
                contacts = {
                    k: (AttendeeService.normalize_phone_number(v) if k.startswith("phone") or k.startswith("whatsapp") else v)
                    for k, v in raw_contacts.items()
                }

            contact_type = (att_data.get("contact_type") or "phone").strip().lower()
            contact_value = (att_data.get("contact_value") or "").strip()
            if contact_value and not contacts:
                if contact_type in ("phone", "whatsapp"):
                    contact_value = AttendeeService.normalize_phone_number(contact_value)
                key = contact_type if contact_type.endswith("1") else f"{contact_type}1"
                contacts[key] = contact_value
                contacts[contact_type] = contact_value
            elif att_data.get("phone") and "phone" not in contacts:
                ph = AttendeeService.normalize_phone_number(att_data.get("phone").strip())
                contacts["phone1"] = ph
                contacts["phone"] = ph
            if att_data.get("email") and "email" not in contacts:
                em = att_data.get("email").strip()
                contacts["email1"] = em
                contacts["email"] = em

            infos = {"fixed": fixed}
            if contacts:
                infos["contacts"] = contacts

            division_id = att_data.get("division_id") or att_data.get("division")
            att_div = None
            if division_id:
                att_div = Division.objects.filter(pk=division_id, organization=current_user.organization).first()
            if not att_div:
                att_div = meet.assembly.division

            validated_attendees.append({
                "first_name": first_name,
                "last_name": last_name,
                "first_name2": first_name2,
                "last_name2": last_name2,
                "gender": gender,
                "division": att_div,
                "actual_birthday": actual_birthday,
                "estimated_birthday": estimated_birthday,
                "infos": infos,
            })

        # 2. Validate guardian / companion data
        special_check_in = None
        if unaccompanied:
            special_check_in = "⚠Missing companion info"
        else:
            if companions:
                for idx, c in enumerate(companions):
                    c_first = (c.get("first_name") or "").strip() or None
                    c_last = (c.get("last_name") or "").strip() or None
                    c_first2 = (c.get("first_name2") or "").strip() or None
                    c_last2 = (c.get("last_name2") or "").strip() or None
                    if not (c_first or c_last or c_first2 or c_last2):
                        raise ValidationError({"companions": f"Companion {idx + 1} name is required."})

                    c_phone = (c.get("phone") or "").strip()
                    c_contact_val = (c.get("contact_value") or "").strip()
                    c_contacts_list = c.get("contacts") or []
                    has_contact = bool(c_phone or c_contact_val or c_contacts_list)
                    if is_kid_meet and not has_contact:
                        raise ValidationError({"companions": f"Companion {idx + 1} contact number or account is required."})
            elif is_kid_meet:
                raise ValidationError({"unaccompanied": "Companion information is required unless 'Child arrived alone' is checked."})

        # 3. Atomic database operations
        with transaction.atomic():
            division = meet.assembly.division

            created_attendees = []
            for item in validated_attendees:
                attendee = Attendee.objects.create(
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    first_name2=item["first_name2"],
                    last_name2=item["last_name2"],
                    gender=item["gender"],
                    division=item["division"],
                    actual_birthday=item["actual_birthday"],
                    estimated_birthday=item["estimated_birthday"],
                    infos=item["infos"],
                )
                created_attendees.append(attendee)

            created_companions = []
            if not unaccompanied and companions:
                for c_data in companions:
                    c_first = (c_data.get("first_name") or "").strip() or None
                    c_last = (c_data.get("last_name") or "").strip() or None
                    c_first2 = (c_data.get("first_name2") or "").strip() or None
                    c_last2 = (c_data.get("last_name2") or "").strip() or None
                    c_gender = c_data.get("gender") or GenderEnum.UNSPECIFIED.value

                    c_contacts = {}
                    raw_c_contacts = c_data.get("contacts")
                    if isinstance(raw_c_contacts, list):
                        type_counts = {}
                        for c in raw_c_contacts:
                            ct = (c.get("type") or "phone").strip().lower()
                            cv = (c.get("value") or "").strip()
                            if cv:
                                if ct in ("phone", "whatsapp"):
                                    cv = AttendeeService.normalize_phone_number(cv)
                                type_counts[ct] = type_counts.get(ct, 0) + 1
                                c_idx = type_counts[ct]
                                c_contacts[f"{ct}{c_idx}"] = cv
                                if c_idx == 1:
                                    c_contacts[ct] = cv
                    elif isinstance(raw_c_contacts, dict):
                        c_contacts = {
                            k: (AttendeeService.normalize_phone_number(v) if k.startswith("phone") or k.startswith("whatsapp") else v)
                            for k, v in raw_c_contacts.items()
                        }

                    c_contact_type = (c_data.get("contact_type") or "phone").strip().lower()
                    c_contact_val = (c_data.get("contact_value") or "").strip()
                    if c_contact_val and not c_contacts:
                        if c_contact_type in ("phone", "whatsapp"):
                            c_contact_val = AttendeeService.normalize_phone_number(c_contact_val)
                        key = c_contact_type if c_contact_type.endswith("1") else f"{c_contact_type}1"
                        c_contacts[key] = c_contact_val
                        c_contacts[c_contact_type] = c_contact_val
                    elif c_data.get("phone") and "phone" not in c_contacts:
                        ph = AttendeeService.normalize_phone_number(c_data.get("phone").strip())
                        c_contacts["phone1"] = ph
                        c_contacts["phone"] = ph
                    if c_data.get("email") and "email" not in c_contacts:
                        em = c_data.get("email").strip()
                        c_contacts["email1"] = em
                        c_contacts["email"] = em

                    c_division_id = c_data.get("division_id") or c_data.get("division")
                    c_division = None
                    if c_division_id:
                        c_division = Division.objects.filter(pk=c_division_id, organization=current_user.organization).first()
                    if not c_division:
                        c_division = division

                    companion_attendee = Attendee.objects.create(
                        first_name=c_first,
                        last_name=c_last,
                        first_name2=c_first2,
                        last_name2=c_last2,
                        gender=c_gender,
                        division=c_division,
                        infos={"contacts": c_contacts} if c_contacts else {},
                    )
                    created_companions.append((companion_attendee, c_data))

            # Folk and FolkAttendee relations
            if not unaccompanied and (created_companions or len(created_attendees) > 1):
                if is_kid_meet:
                    for c_idx, (comp_attendee, c_data) in enumerate(created_companions):
                        c_rel = c_data.get("relationship") or c_data.get("relation_id")
                        comp_role = None
                        if c_rel:
                            if str(c_rel).isdigit():
                                comp_role = Relation.objects.filter(pk=int(c_rel), is_removed=False).first()
                            else:
                                comp_role = Relation.objects.filter(title__iexact=str(c_rel).strip(), is_removed=False).first()

                        if not comp_role:
                            norm_cg = str(comp_attendee.gender).strip().lower()
                            if norm_cg == "male":
                                comp_role = Relation.objects.filter(title__iexact="father", is_removed=False).first()
                            elif norm_cg == "female":
                                comp_role = Relation.objects.filter(title__iexact="mother", is_removed=False).first()
                            if not comp_role:
                                comp_role = (
                                    Relation.objects.filter(title__iexact="parent", is_removed=False).first()
                                    or Relation.objects.filter(emergency_contact=True).first()
                                    or Relation.objects.filter(id=1).first()
                                    or Relation.objects.first()
                                )

                        recip_role = None
                        if comp_role and comp_role.reciprocal_ids:
                            recips = list(Relation.objects.filter(pk__in=comp_role.reciprocal_ids, is_removed=False))
                            if comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                                recip_role = next((r for r in recips if r.title.lower() in ("ward", "care receiver")), None)
                            else:
                                recip_role = next((r for r in recips if r.title.lower() == "child"), None)
                            if not recip_role and recips:
                                recip_role = recips[0]

                        if not recip_role and comp_role and comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                            recip_role = Relation.objects.filter(title__iexact="ward").first()

                        if not recip_role:
                            recip_role = (
                                Relation.objects.filter(title__iexact="child").first()
                                or Relation.objects.filter(id=2).first()
                                or Relation.objects.first()
                            )

                        is_family = bool(
                            comp_role and (
                                comp_role.consanguinity
                                or (comp_role.title and comp_role.title.lower() in ("parent", "father", "mother", "child", "son", "daughter", "brother", "sister", "husband", "wife", "spouse"))
                            )
                        )

                        if is_family:
                            primary_kid = created_attendees[0]
                            family_folk = (
                                primary_kid.folks.filter(category=Attendee.FAMILY_CATEGORY).first()
                                or comp_attendee.folks.filter(category=Attendee.FAMILY_CATEGORY).first()
                            )
                            if not family_folk:
                                family_cat, _ = Category.objects.get_or_create(
                                    id=Attendee.FAMILY_CATEGORY,
                                    defaults={"display_name": "Family", "type": "folk"},
                                )
                                family_name = (
                                    comp_attendee.last_name or comp_attendee.last_name2
                                    or primary_kid.last_name or primary_kid.first_name
                                )
                                family_folk = Folk.objects.create(
                                    category=family_cat,
                                    division=comp_attendee.division,
                                    display_name=f"{family_name} family",
                                )

                            FolkAttendee.objects.update_or_create(
                                folk=family_folk,
                                attendee=comp_attendee,
                                defaults={"role": comp_role, "display_order": c_idx + 1},
                            )

                            for k_idx, kid in enumerate(created_attendees):
                                if comp_role and comp_role.title and comp_role.title.lower() in ("guardian", "caregiver"):
                                    kid_role = recip_role
                                else:
                                    norm_kid_gender = str(kid.gender).strip().lower()
                                    if norm_kid_gender == "male":
                                        kid_role = (
                                            Relation.objects.filter(title__iexact="son", is_removed=False).first()
                                            or recip_role
                                        )
                                    elif norm_kid_gender == "female":
                                        kid_role = (
                                            Relation.objects.filter(title__iexact="daughter", is_removed=False).first()
                                            or recip_role
                                        )
                                    else:
                                        kid_role = recip_role

                                kid_fa_defaults = {
                                    "role": kid_role,
                                    "display_order": 11 + k_idx,
                                }
                                if kid.actual_birthday:
                                    kid_fa_defaults["start"] = kid.actual_birthday

                                FolkAttendee.objects.update_or_create(
                                    folk=family_folk,
                                    attendee=kid,
                                    defaults=kid_fa_defaults,
                                )
                        else:
                            for k_idx, kid in enumerate(created_attendees):
                                kid_other_folk = kid.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                                if not kid_other_folk:
                                    kid_name_str = (kid.infos.get("names", {}).get("original") or kid.display_label).strip()
                                    kid_other_folk = AttendeeService.create_or_update_first_folk(
                                        kid,
                                        f"{kid_name_str} other",
                                        Attendee.NON_FAMILY_CATEGORY,
                                        Attendee.HIDDEN_ROLE,
                                        False,
                                    )

                                FolkAttendee.objects.update_or_create(
                                    folk=kid_other_folk,
                                    attendee=comp_attendee,
                                    defaults={"role": comp_role, "display_order": c_idx + 1},
                                )

                                kid_fa_defaults = {
                                    "role": recip_role,
                                    "display_order": 11 + k_idx,
                                }
                                if kid.actual_birthday:
                                    kid_fa_defaults["start"] = kid.actual_birthday

                                comp_other_folk = comp_attendee.folks.filter(category=Attendee.NON_FAMILY_CATEGORY).first()
                                if comp_other_folk:
                                    FolkAttendee.objects.update_or_create(
                                        folk=comp_other_folk,
                                        attendee=kid,
                                        defaults=kid_fa_defaults,
                                    )

                        # Set emergency contacts
                        if comp_role and (comp_role.emergency_contact or (comp_role.title and comp_role.title.lower() in ("parent", "father", "mother", "guardian", "caregiver"))):
                            for kid in created_attendees:
                                kid.infos.setdefault("emergency_contacts", {})[str(comp_attendee.id)] = True
                                comp_attendee.infos.setdefault("emergency_contacts", {})[str(kid.id)] = getattr(recip_role, "emergency_contact", False)
                                kid.save(update_fields=["infos"])
                            comp_attendee.save(update_fields=["infos"])
                else:
                    # Adult meet: establish family folk with husband (rank 1), wife (rank 2), spouse
                    all_family_members = list(created_attendees) + [c[0] for c in created_companions]
                    primary_adult = created_attendees[0]
                    first_comp = created_companions[0][0] if created_companions else None
                    family_name = (
                        (first_comp.last_name or first_comp.last_name2)
                        if first_comp and (first_comp.last_name or first_comp.last_name2)
                        else (primary_adult.last_name or primary_adult.last_name2 or primary_adult.first_name)
                    )
                    family_cat, _ = Category.objects.get_or_create(
                        id=Attendee.FAMILY_CATEGORY,
                        defaults={"display_name": "Family", "type": "folk"},
                    )
                    family_folk = (
                        primary_adult.folks.filter(category=Attendee.FAMILY_CATEGORY).first()
                        or (first_comp.folks.filter(category=Attendee.FAMILY_CATEGORY).first() if first_comp else None)
                    )
                    if not family_folk:
                        family_folk = Folk.objects.create(
                            category=family_cat,
                            division=primary_adult.division,
                            display_name=f"{family_name} family",
                        )

                    husband_role = (
                        Relation.objects.filter(title__iexact="husband", is_removed=False).first()
                        or Relation.objects.filter(id=5).first()
                    )
                    wife_role = (
                        Relation.objects.filter(title__iexact="wife", is_removed=False).first()
                        or Relation.objects.filter(id=6).first()
                    )
                    spouse_role = (
                        Relation.objects.filter(title__iexact="spouse", is_removed=False).first()
                        or Relation.objects.filter(id=14).first()
                        or Relation.objects.first()
                    )
                    son_role = (
                        Relation.objects.filter(title__iexact="son", is_removed=False).first()
                        or Relation.objects.filter(id=3).first()
                    )
                    daughter_role = (
                        Relation.objects.filter(title__iexact="daughter", is_removed=False).first()
                        or Relation.objects.filter(id=4).first()
                    )
                    child_role = (
                        Relation.objects.filter(title__iexact="child", is_removed=False).first()
                        or Relation.objects.filter(id=27).first()
                        or son_role
                    )

                    has_husband = False
                    has_wife = False
                    child_count = 0

                    for m_idx, member in enumerate(all_family_members):
                        m_gender = str(member.gender or "").strip().lower()
                        # Starting from 3rd member (m_idx >= 2), assign child role (son/daughter/child, rank 11+)
                        if m_idx >= 2:
                            if m_gender == "male":
                                m_role = son_role
                            elif m_gender == "female":
                                m_role = daughter_role
                            else:
                                m_role = child_role
                            m_order = 11 + child_count
                            child_count += 1
                        else:
                            # First two members: husband and wife with exclusivity
                            if m_gender == "male":
                                if not has_husband:
                                    m_role = husband_role
                                    m_order = 1
                                    has_husband = True
                                else:
                                    m_role = son_role
                                    m_order = 11 + child_count
                                    child_count += 1
                            elif m_gender == "female":
                                if not has_wife:
                                    m_role = wife_role
                                    m_order = 2
                                    has_wife = True
                                else:
                                    m_role = daughter_role
                                    m_order = 11 + child_count
                                    child_count += 1
                            else:
                                # Unspecified gender
                                if not has_husband:
                                    m_role = husband_role or spouse_role
                                    m_order = 1
                                    has_husband = True
                                elif not has_wife:
                                    m_role = wife_role or spouse_role
                                    m_order = 2
                                    has_wife = True
                                else:
                                    m_role = child_role
                                    m_order = 11 + child_count
                                    child_count += 1

                        m_defaults = {
                            "role": m_role,
                            "display_order": m_order,
                        }
                        if member.actual_birthday:
                            m_defaults["start"] = member.actual_birthday

                        FolkAttendee.objects.update_or_create(
                            folk=family_folk,
                            attendee=member,
                            defaults=m_defaults,
                        )

                    for att in created_attendees:
                        for comp_att, _ in created_companions:
                            att.infos.setdefault("emergency_contacts", {})[str(comp_att.id)] = True
                            comp_att.infos.setdefault("emergency_contacts", {})[str(att.id)] = True
                            comp_att.save(update_fields=["infos"])
                        att.save(update_fields=["infos"])

            # 4. Attending & AttendingMeet & Attendance for all created attendees
            scheduled_cat = (
                Category.objects.filter(id=Attendee.SCHEDULED_CATEGORY).first()
                or Category.objects.filter(id=1).first()
            )
            major_char = meet.major_character or Character.objects.filter(assembly=meet.assembly).first()

            gathering = None
            if gathering_id:
                if str(gathering_id).isdigit():
                    gathering = Gathering.objects.filter(pk=int(gathering_id), meet=meet, is_removed=False).first()
                elif str(gathering_id).startswith("start_"):
                    occ_iso = str(gathering_id).replace("start_", "")
                    from django.utils.dateparse import parse_datetime
                    occ_dt = parse_datetime(occ_iso)
                    if occ_dt:
                        gathering = Gathering.objects.filter(meet=meet, start=occ_dt, is_removed=False).first()
                        if not gathering:
                            site_type = meet.site_type or (ContentType.objects.get_for_model(meet.assembly) if getattr(meet, 'assembly', None) else None) or ContentType.objects.get_for_model(Meet)
                            site_id = str(meet.site_id) if meet.site_id else (str(meet.assembly.id) if getattr(meet, 'assembly', None) else str(meet.id))
                            gathering = Gathering.objects.create(
                                meet=meet,
                                display_name=f"{meet.display_name} {occ_dt.strftime('%Y-%m-%d %H:%M')}",
                                start=occ_dt,
                                finish=occ_dt + timedelta(hours=2),
                                site_type=site_type,
                                site_id=site_id,
                            )

            if not gathering:
                now = Utility.now_with_timezone()
                gathering = (
                    Gathering.objects.filter(
                        meet=meet,
                        start__lte=now,
                        finish__gte=now,
                        is_removed=False,
                    ).first()
                    or Gathering.objects.filter(
                        meet=meet,
                        start__gte=now - timedelta(hours=2),
                        is_removed=False,
                    ).order_by("start").first()
                    or Gathering.objects.filter(
                        meet=meet,
                        is_removed=False,
                    ).order_by("-start").first()
                )

            if not gathering:
                now = Utility.now_with_timezone()
                site_type = meet.site_type or (ContentType.objects.get_for_model(meet.assembly) if getattr(meet, 'assembly', None) else None) or ContentType.objects.get_for_model(Meet)
                site_id = str(meet.site_id) if meet.site_id else (str(meet.assembly.id) if getattr(meet, 'assembly', None) else str(meet.id))
                gathering = Gathering.objects.create(
                    meet=meet,
                    display_name=f"{meet.display_name} {now.strftime('%Y-%m-%d')}",
                    start=now,
                    finish=now + timedelta(hours=2),
                    site_type=site_type,
                    site_id=site_id,
                )

            attended_cat = (
                Category.objects.filter(id=Attendee.ATTENDED_CATEGORY).first()
                or Category.objects.filter(type="attendance", display_name__iexact="attended").first()
                or Category.objects.filter(type="attendance").exclude(id=1).first()
            )

            created_attendees_info = []
            for att in created_attendees:
                attending = att.attendings.first()
                if not attending:
                    attending = Attending.objects.create(
                        attendee=att,
                        category="auto-created",
                        infos={"created_reason": "fast onboarding"},
                    )

                am_infos = {"created_reason": "fast onboarding"}
                if special_check_in:
                    am_infos["special"] = {"check_in": special_check_in}

                attendingmeet = AttendingMeet.objects.create(
                    attending=attending,
                    meet=meet,
                    character=major_char,
                    category=scheduled_cat,
                    finish=Utility.now_with_timezone() + timedelta(weeks=meet.infos.get('default_attendingmeet_in_weeks', 99999)),
                    infos=am_infos,
                )

                attendance = None
                if gathering:
                    attendance = Attendance.objects.create(
                        gathering=gathering,
                        attending=attending,
                        character=major_char,
                        category=attended_cat or Category.objects.get(pk=Attendee.ATTENDED_CATEGORY),
                        start=Utility.now_with_timezone(),
                    )

                created_attendees_info.append({
                    "attendee_id": att.id,
                    "attendee_name": att.display_label,
                    "first_name": att.first_name,
                    "last_name": att.last_name,
                    "first_name2": att.first_name2,
                    "last_name2": att.last_name2,
                    "gender": att.gender,
                    "actual_birthday": str(att.actual_birthday) if att.actual_birthday else None,
                    "estimated_birthday": str(att.estimated_birthday) if att.estimated_birthday else None,
                    "attending_id": attending.id,
                    "attendingmeet_id": attendingmeet.id,
                    "attendance_id": attendance.id if attendance else None,
                })

            primary = created_attendees_info[0]
            comp_objs = [c[0] for c in created_companions]
            return {
                "attendee_id": primary["attendee_id"],
                "attendee_name": primary["attendee_name"],
                "first_name": primary["first_name"],
                "last_name": primary["last_name"],
                "first_name2": primary["first_name2"],
                "last_name2": primary["last_name2"],
                "gender": primary["gender"],
                "actual_birthday": primary["actual_birthday"],
                "estimated_birthday": primary["estimated_birthday"],
                "attending_id": primary["attending_id"],
                "attendingmeet_id": primary["attendingmeet_id"],
                "attendance_id": primary["attendance_id"],
                "gathering_id": gathering.id if gathering else None,
                "warning": special_check_in,
                "parent_id": comp_objs[0].id if comp_objs else None,
                "companion_ids": [c.id for c in comp_objs],
                "is_kid_meet": is_kid_meet,
                "attendees": created_attendees_info,
                "attendee_ids": [info["attendee_id"] for info in created_attendees_info],
            }



