from datetime import datetime, timedelta

import pytz
from address.models import Address
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from rest_framework.utils import json

from attendees.occasions.models import Gathering, Meet
from attendees.whereabouts.models import Room, Suite, Property, Campus, Division, Organization


class GatheringService:
    SITE_SEARCHING_PROPERTIES = {
        Room: 'display_name',
        Suite: 'display_name',
        Property: 'display_name',
        Campus: 'display_name',
        Division: 'display_name',
        Organization: 'display_name',
        Address: 'formatted',
    }

    @staticmethod
    def by_assembly_meets(assembly_slug, meet_slugs):
        return Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__slug=assembly_slug,
        ).order_by(
            "meet",
            "-start",
        )

    @staticmethod
    def by_family_meets(user, meet_slugs):
        """
        :query: Find all gatherings of all Attendances of the current user and their kid/care receiver, so all
                their "family" attending gatherings (including not joined characters) will show up.
        :param user: user object
        :param meet_slugs:
        :return:  all Gatherings of the logged in user and their kids/care receivers.
        """
        return Gathering.objects.filter(
            Q(meet__in=user.attendee.attendings.values_list("gathering__meet")),
            # |
            # Q(meet__in=user.attendee.related_ones.filter(
            #     from_attendee__scheduler=True
            # ).values_list('attendings__gathering__meet')),
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization__slug=user.organization.slug,
        ).order_by(
            "meet",
            "-start",
        )  # another way is to get assemblys from registration, but it relies on attendingmeet validations

    @staticmethod
    def by_organization_meets(current_user, meet_slugs, start, finish, orderbys, filter, search_value, search_expression=None, search_operation=None,):
        orderby_list = GatheringService.orderby_parser(orderbys)
        extra_filters = Q(
            meet__assembly__division__organization__slug=current_user.organization.slug
        ).add(Q(meet__slug__in=meet_slugs), Q.AND)
        # Todo 20220512 let scheduler see other attendings too?
        if not current_user.can_see_all_organizational_meets_attendees():
            extra_filters.add((Q(attendings__attendee__in=current_user.attendee.scheduling_attendees())
                               |
                               Q(attendings__registration__registrant=current_user.attendee)), Q.AND)

        if search_value and search_operation == 'contains' and search_expression in ['display_name', 'gathering_label']:  # for searching in drop down of popup editor
            extra_filters.add((Q(display_name__icontains=search_value)
                               |
                               Q(infos__icontains=search_value)), Q.AND)

        if filter:  # [["meet","=",1],"or",["meet","=",2]] is already filtered by slugs above
            filter_term = json.loads(filter)  # [["display_name","contains","207"],"or",["site","contains","207"]]
            if isinstance(filter_term[0], list) and filter_term[0][1] == 'contains':
                search_term = filter_term[0][2]
                if search_term:  # for searching in the upper right search bar of datagrid
                    search_filters = Q(display_name__icontains=search_term)    # Gathering level
                    search_filters.add(Q(infos__icontains=search_term), Q.OR)  # Gathering level

                    for site, field in GatheringService.SITE_SEARCHING_PROPERTIES.items():
                        site_filter = {f"{field}__icontains": search_term}
                        search_filters.add(
                            (Q(site_type__model=site._meta.model_name)
                             &
                             Q(site_id__in=[str(key)  # can't use site_id__regex=r'(1|2|3)' for empty r'()'
                                            for key in site.objects.filter(**site_filter).values_list('id', flat=True)]
                               )
                             ), Q.OR)

                    extra_filters.add(search_filters, Q.AND)

        if start:
            extra_filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
        if finish:
            extra_filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)
        return Gathering.objects.filter(extra_filters).order_by(*orderby_list)

    @staticmethod
    def batch_create(begin, end, meet_slug, duration, meet, user_time_zone):
        """
        Idempotently create gatherings based on the following params.  Created Gatherings are associated with Occurrence

        :param begin: ISO format datetime string
        :param end: ISO format datetime string
        :param meet_slug: meet slug for error reporting
        :param duration: gathering duration in minutes
        :param meet: Meet instance
        :param user_time_zone: DEPRECATED - timezone is now derived from meet.infos['default_time_zone'] since users can be anywhere
        :return: dict with success status and number of gatherings created
        """
        number_created = 0
        iso_time_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        user_begin_time = datetime.strptime(begin, iso_time_format)
        user_end_time = datetime.strptime(end, iso_time_format)

        # Validate that meet has default_time_zone configured
        if not meet or not meet.infos.get('default_time_zone'):
            results = {
                "success": False,
                "number_created": 0,
                "meet_slug": meet.slug if meet else meet_slug,
                "begin": begin,
                "end": end,
                "explain": (
                    f"CRITICAL: Meet '{meet.slug if meet else meet_slug}' must have "
                    f"'default_time_zone' configured in infos to avoid timezone ambiguity. "
                    f"Please set meet.infos['default_time_zone'] (e.g., 'America/Los_Angeles')."
                ),
            }
            return results

        # Use meet's canonical timezone instead of user_time_zone parameter
        canonical_time_zone = pytz.timezone(meet.infos['default_time_zone'])

        if meet and user_end_time > user_begin_time:
            begin_time = (
                user_begin_time if meet.start < user_begin_time else meet.start
            ).astimezone(canonical_time_zone)
            end_time = (
                user_end_time if meet.finish > user_end_time else meet.finish
            ).astimezone(canonical_time_zone)
            gathering_time = (
                timedelta(minutes=duration) if duration and duration > 0 else None
            )
            for er in meet.event_relations.all():  # changing source/location/user's events all together
                for occurrence in er.event.get_occurrences(begin_time, end_time):
                    if not occurrence.cancelled:
                        occurrence_end = (
                            occurrence.start + gathering_time
                            if gathering_time
                            else occurrence.end
                        )
                        site_type = meet.site_type
                        site_id = meet.site_id
                        site_info = er.event.description
                        model_name = site_type.model

                        if site_info:
                            model_name, site_id = site_info.split("#")
                            model = ContentType.objects.filter(model=model_name).first()
                            site_type = ContentType.objects.get_for_model(model.model_class())

                        infos = {**meet.infos.get('gathering_infos', {}), 'created_reason': 'batch created'}  # prevent occurrence created again by signal
                        if er.distinction != 'source':
                            del infos['generate_attendance']  # no attendance will be generated for every location calendar

                        # Force timezone conversion to canonical timezone to prevent duplicates
                        canonical_start = occurrence.start.astimezone(canonical_time_zone)
                        canonical_end = occurrence_end.astimezone(canonical_time_zone)

                        gathering, gathering_created = Gathering.objects.get_or_create(
                            meet=meet,
                            site_id=site_id,
                            site_type=site_type,
                            start=canonical_start,
                            defaults={
                                "site_type": site_type,
                                "site_id": site_id,
                                "meet": meet,
                                "start": canonical_start,
                                "finish": canonical_end,
                                "infos": infos,
                                "display_name": f'{meet.display_name} {canonical_start.strftime("%Y/%m/%d,%H:%M %p %Z")} at {meet.site}'[0:254],
                            },
                        )  # don't update gatherings if exist since it may have customizations

                        if gathering_created:
                            number_created += 1

                        if not occurrence.id:
                            occurrence.title = f'gathering#{gathering.id}'
                            occurrence.description = f'{model_name}#{site_id}'
                            occurrence.save()

            results = {
                "success": True,
                "number_created": number_created,
                "meet_slug": meet.slug,
                "begin": begin_time,
                "end": end_time,
                "explain": "Begin&end dates are restrained by Event's default dates.",
            }

        else:
            results = {
                "success": False,
                "number_created": number_created,
                "meet_slug": meet_slug,
                "begin": begin,
                "end": end,
                "explain": "Meet or begin&end time invalid.",
            }

        return results

    @staticmethod
    def orderby_parser(orderbys):
        """
        generates sorter (column) based on user's choice
        # Sort by site name is NOT supported https://stackoverflow.com/a/3967871/4257237
        :param orderbys: list of search params
        :return: a List of sorter for order_by()
        """
        orderby_list = (
            []
        )  # sort attendingmeets is [{"selector":"<<dataField value in DataGrid>>","desc":false}]

        for orderby_dict in orderbys:
            field = orderby_dict.get("selector", "id").replace(".", "__")
            direction = "-" if orderby_dict.get("desc", False) else ""
            if field == "site":
                site_columns = [
                    direction + "site_type",  # same types of sites will be grouped together
                    direction + "site_id",    # but site__display_name is not supported
                ]
                orderby_list.extend(site_columns)
            else:
                orderby_list.append(direction + field)
        return orderby_list

    @staticmethod
    def get_or_create_single_gathering(meet, start_time):
        """
        Idempotently get or create a single gathering for a meet and start time.
        Uses the meet's source EventRelation to determine duration and site if creating.

        :param meet: Meet instance, or meet_id (int/str), or meet_slug (str)
        :param start_time: datetime or ISO format datetime string
        :return: (gathering, created) tuple
        """
        if isinstance(meet, Meet):
            meet_obj = meet
        elif isinstance(meet, (int, str)):
            if str(meet).isdigit():
                meet_obj = Meet.objects.filter(pk=int(meet)).first()
            else:
                meet_obj = Meet.objects.filter(slug=meet).first()
        else:
            meet_obj = None

        if not meet_obj:
            raise ValueError(f"Meet not found for: {meet}")

        if isinstance(start_time, str):
            parsed_dt = parse_datetime(start_time)
            if parsed_dt is None:
                from dateutil.parser import parse
                parsed_dt = parse(start_time)
        else:
            parsed_dt = start_time

        tz_name = meet_obj.infos.get('default_time_zone') or settings.TIME_ZONE
        canonical_time_zone = pytz.timezone(tz_name)
        if parsed_dt.tzinfo is None:
            canonical_start = canonical_time_zone.localize(parsed_dt)
        else:
            canonical_start = parsed_dt.astimezone(canonical_time_zone)

        # Check by meet and start time within a 30 second window
        start_min = canonical_start - timedelta(seconds=30)
        start_max = canonical_start + timedelta(seconds=30)
        existing = Gathering.objects.filter(
            meet=meet_obj,
            start__gte=start_min,
            start__lte=start_max,
            is_removed=False,
        ).first()

        if existing:
            return existing, False

        site_type = meet_obj.site_type
        site_id = meet_obj.site_id
        canonical_end = None

        source_er = meet_obj.event_relations.filter(distinction='source').first()
        if not source_er:
            source_er = meet_obj.event_relations.first()

        if source_er:
            site_info = source_er.event.description
            if site_info and '#' in site_info:
                model_name, s_id = site_info.split("#")
                model = ContentType.objects.filter(model=model_name).first()
                if model:
                    site_type = ContentType.objects.get_for_model(model.model_class())
                    site_id = s_id

            # Determine occurrence duration
            occs = source_er.event.get_occurrences(
                canonical_start - timedelta(minutes=5),
                canonical_start + timedelta(minutes=5)
            )
            for occ in occs:
                if not occ.cancelled:
                    canonical_end = occ.end.astimezone(canonical_time_zone)
                    break

        if not canonical_end:
            canonical_end = canonical_start + timedelta(hours=1)

        infos = {**meet_obj.infos.get('gathering_infos', {}), 'created_reason': 'auto created on attendance'}
        site_name = ""
        if meet_obj.site:
            try:
                site_name = str(meet_obj.site)
            except Exception:
                site_name = getattr(meet_obj.site, 'display_name', '')

        gathering, created = Gathering.objects.get_or_create(
            meet=meet_obj,
            site_id=site_id,
            site_type=site_type,
            start=canonical_start,
            defaults={
                "site_type": site_type,
                "site_id": site_id,
                "meet": meet_obj,
                "start": canonical_start,
                "finish": canonical_end,
                "infos": infos,
                "display_name": f'{meet_obj.display_name} {canonical_start.strftime("%Y/%m/%d,%H:%M %p %Z")} at {site_name}'[0:254],
            },
        )
        return gathering, created

    @staticmethod
    def get_roster_gatherings(organization, meet_slugs, start, finish):
        """
        Returns a list of gathering column dicts for rosters datagrid.
        Merges existing database gatherings and future occurrences forecasted from meet source event relations.
        """
        if isinstance(start, str):
            start_dt = parse_datetime(start)
        else:
            start_dt = start

        if isinstance(finish, str):
            finish_dt = parse_datetime(finish)
        else:
            finish_dt = finish

        existing_gatherings_qs = Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization=organization,
            is_removed=False,
        )
        if start_dt:
            existing_gatherings_qs = existing_gatherings_qs.filter(start__gte=start_dt)
        if finish_dt:
            existing_gatherings_qs = existing_gatherings_qs.filter(finish__lte=finish_dt)

        existing_gatherings = list(existing_gatherings_qs.order_by('start', 'meet__display_name', 'id'))

        columns = []
        existing_keys = set()
        for g in existing_gatherings:
            columns.append({
                "id": g.id,
                "display_name": g.display_name,
                "start": g.start.isoformat() if g.start else None,
                "meet_id": g.meet_id,
                "_start_dt": g.start,
            })
            if g.start:
                utc_start = g.start.astimezone(pytz.utc)
                key = (g.meet_id, int(utc_start.timestamp() // 60))
                existing_keys.add(key)

        meets = Meet.objects.filter(
            slug__in=meet_slugs,
            assembly__division__organization=organization,
            is_removed=False,
        )
        for meet in meets:
            tz_name = meet.infos.get('default_time_zone') or settings.TIME_ZONE
            canonical_tz = pytz.timezone(tz_name)

            m_start = start_dt
            if meet.start and (not m_start or meet.start > m_start):
                m_start = meet.start

            m_finish = finish_dt
            if meet.finish and (not m_finish or meet.finish < m_finish):
                m_finish = meet.finish

            if not m_start or not m_finish or m_start >= m_finish:
                continue

            begin_time = m_start.astimezone(canonical_tz) if m_start.tzinfo else canonical_tz.localize(m_start)
            end_time = m_finish.astimezone(canonical_tz) if m_finish.tzinfo else canonical_tz.localize(m_finish)

            for er in meet.event_relations.filter(distinction='source'):
                for occ in er.event.get_occurrences(begin_time, end_time):
                    if occ.cancelled:
                        continue
                    occ_start = occ.start.astimezone(canonical_tz)
                    if occ_start < begin_time or occ_start > end_time:
                        continue
                    utc_occ_start = occ_start.astimezone(pytz.utc)
                    key = (meet.id, int(utc_occ_start.timestamp() // 60))
                    if key in existing_keys:
                        continue
                    site_name = ""
                    if meet.site:
                        try:
                            site_name = str(meet.site)
                        except Exception:
                            site_name = getattr(meet.site, 'display_name', '')

                    display_name = f'{meet.display_name} {occ_start.strftime("%Y/%m/%d,%H:%M %p %Z")} at {site_name}'[0:254]
                    columns.append({
                        "id": None,
                        "display_name": display_name,
                        "start": occ_start.isoformat(),
                        "meet_id": meet.id,
                        "_start_dt": occ_start,
                    })

        columns.sort(key=lambda col: (col["_start_dt"].astimezone(pytz.utc) if col.get("_start_dt") else datetime.min.replace(tzinfo=pytz.utc), col.get("meet_id") or 0))
        for col in columns:
            col.pop("_start_dt", None)

        return columns
