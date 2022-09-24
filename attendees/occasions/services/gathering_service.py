from datetime import datetime, timedelta

from address.models import Address
from django.contrib.contenttypes.models import ContentType
from rest_framework.utils import json
from django.db.models import Q

from attendees.occasions.models import Gathering
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
        Todo 20210821 Hardcoded tzinfo for strptime to get event.get_occurrences() working as of now, needs improvement.
        :param begin:
        :param end:
        :param meet_slug:
        :param duration:
        :param meet:
        :param user_time_zone:
        :return: number of gatherings created
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
            gathering_time = (
                timedelta(minutes=duration) if duration and duration > 0 else None
            )
            for er in meet.event_relations.all():
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

                        if site_info:
                            model_name, site_id = site_info.split("#")
                            model = ContentType.objects.filter(model=model_name).first()
                            site_type = ContentType.objects.get_for_model(model.model_class())

                        gathering, gathering_created = Gathering.objects.get_or_create(
                            meet=meet,
                            site_id=site_id,
                            site_type=site_type,
                            start=occurrence.start,
                            defaults={
                                "site_type": site_type,
                                "site_id": site_id,
                                "meet": meet,
                                "start": occurrence.start,
                                "finish": occurrence_end,
                                "infos": {**meet.infos.get('gathering_infos', {}), 'created_reason': 'batch created'},  # prevent occurrence created again by signal
                                "display_name": f'{occurrence.start.strftime("%Y/%m/%d,%H:%M %p %Z")} at {meet.site}'[0:254],
                            },
                        )  # don't update gatherings if exist since it may have customizations

                        if gathering_created:
                            occurrence.title = f'gathering#{gathering.id}'
                            occurrence.description = f'{model_name}#{site_id}'
                            occurrence.save()
                            number_created += 1

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
