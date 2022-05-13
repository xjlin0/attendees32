from datetime import datetime, timedelta

from django.db.models import F, Func, Q
from django.db.models.expressions import OrderBy

from attendees.occasions.models import Gathering, Meet


class GatheringService:
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
    def by_organization_meets(current_user, meet_slugs, start, finish, orderbys):
        orderby_list = GatheringService.orderby_parser(orderbys)
        filters = Q(
            meet__assembly__division__organization__slug=current_user.organization.slug
        ).add(Q(meet__slug__in=meet_slugs), Q.AND)

        if not current_user.can_see_all_organizational_meets_attendees():
            filters.add(Q(attendings__attendee=current_user.attendee), Q.AND)

        if start:
            filters.add((Q(finish__isnull=True) | Q(finish__gte=start)), Q.AND)
        if finish:
            filters.add((Q(start__isnull=True) | Q(start__lte=finish)), Q.AND)
        return Gathering.objects.filter(filters).order_by(*orderby_list)

    @staticmethod
    def batch_create(begin, end, meet_slug, duration, meet, user_time_zone):
        """
        Ideopotently create gatherings based on the following params.  Created Gatherings are associated with Occurrence
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
                    occurrence_end = (
                        occurrence.start + gathering_time
                        if gathering_time
                        else occurrence.end
                    )
                    gathering, gathering_created = Gathering.objects.get_or_create(
                        meet=meet,
                        site_id=meet.site_id,
                        site_type=meet.site_type,
                        start=occurrence.start,
                        defaults={
                            "site_type": meet.site_type,
                            "site_id": meet.site_id,
                            "meet": meet,
                            "start": occurrence.start,
                            "finish": occurrence_end,
                            "infos": meet.infos,
                            "display_name": f'{meet.display_name} {occurrence.start.strftime("%Y/%m/%d,%H:%M %p %Z")}',
                        },
                    )  # don't update gatherings if exist since it may have customizations

                    if gathering_created:
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
        generates sorter (column or OrderBy Func) based on user's choice
        Todo: Sort by site name is NOT supported https://stackoverflow.com/a/3967871/4257237
        :param orderbys: list of search params
        :param meet_slugs: meet slugs
        :param current_user:
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
