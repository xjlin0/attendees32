import re
from datetime import datetime, timezone
from pathlib import Path
from partial_date import PartialDate
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates.general import StringAgg, JSONBAgg
from django.db.models import Case, F, Func, Q, When, CharField, JSONField, Count, Min
from django.db.models.functions import Cast, Substr, Coalesce
from django.db.models.expressions import OrderBy, Value
from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework.utils import json

from attendees.occasions.models import Meet, Gathering
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


