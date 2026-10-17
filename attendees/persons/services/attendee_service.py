from datetime import datetime, timezone
from pathlib import Path
from partial_date import PartialDate
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates.general import StringAgg, JSONBAgg
from django.db.models import Case, F, Func, Q, When, CharField, JSONField, Count, Min
from django.db.models.functions import Cast, Substr, Coalesce
from django.db.models.expressions import OrderBy, Value
from django.http import Http404
from rest_framework.utils import json

from attendees.occasions.models import Meet, Gathering
from attendees.persons.models import (  # , Relationship
    Attendee,
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

        gathering_list = [
            {
                "id": g.id,
                "display_name": g.display_name,
                "start": g.start.isoformat() if g.start else None,
                "meet_id": g.meet_id
            }
            for g in gatherings
        ]

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
                Q(attendings__attendingmeet__team__display_name__icontains=search_value)
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
                    Value('character_id'), 'attendings__attendingmeet__character_id',
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
                "contacts": contacts_str,
                "attendances": attendee.attendances,
                "attendingmeets": attendee.attendingmeets,
                "total_attendances": attendee.total_attendances,
            })

        return gathering_list, rows, total_count

