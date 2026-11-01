import json
import time
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.services import GatheringService, RosterService
from attendees.occasions.serializers import RosterResponseSerializer


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetRostersViewSet(viewsets.ViewSet):
    """
    API endpoint that returns pivoted roster data (gatherings as columns, attendees as rows).
    """

    def list(self, request, *args, **kwargs):
        """
        Retrieves pivoted roster data for specified meets and date range for DevExtreme DataGrid.

        Permissions:
            - Requires authenticated user (`login_required`).
            - Privileged users (belonging to groups configured in `user.organization.infos['groups_see_all_meets_attendees']`,
              evaluated by `request.user.can_see_all_organizational_meets_attendees()`) can view all attendees in the meet.
            - Standard users are restricted to viewing only attendees in their own family (`FAMILY_CATEGORY` folks)
              or themselves. If the user has no linked attendee profile, 0 rows are returned.

        Query Parameters:
            meets[] (list of str, required): Slugs of the meets to query.
            start (str, required): ISO datetime string specifying the start boundary of gatherings.
            finish (str, required): ISO datetime string specifying the finish boundary of gatherings.
            skip (int, optional, default=0): Number of records to skip for pagination.
            take (int, optional, default=40): Number of records to return for pagination.
            sort (str, optional): JSON string describing sorting criteria (e.g., '[{"selector": "attendee_name", "desc": false}]').
            group (str, optional): JSON string describing grouping criteria (e.g., '[{"selector": "team__display_name", "desc": false}]').
            searchValue (str, optional): Substring to search attendee names.
            filter (str, optional): DevExtreme filter JSON expression; parsed as search substring if `searchValue` is not provided.

        Returns:
            Response: DRF Response with status 200 containing:
                - totalCount (int): Total count of attendees matching criteria.
                - columns (list of dict): Gathering column definitions (id, date, title, etc.).
                - rows (list of dict): Flattened or grouped attendee rows containing attendance statuses per gathering.
                - data (list of dict): Alias for `rows` for DevExtreme compatibility.
            Response with status 400 if required parameters (`meets[]`, `start`, `finish`) are missing.
        """
        current_user_organization = request.user.organization
        meet_slugs = request.query_params.getlist("meets[]", [])
        start = request.query_params.get("start")
        finish = request.query_params.get("finish")

        if not meet_slugs or not start or not finish:
            return Response({"error": "meets[], start, and finish are required"}, status=400)

        # Pagination
        try:
            skip = int(request.query_params.get("skip", 0))
        except ValueError:
            skip = 0
            
        try:
            take = int(request.query_params.get("take", 40))
        except ValueError:
            take = 40

        # Sorting
        sort_list = []
        sort_param = request.query_params.get("sort")
        if sort_param:
            try:
                sort_parsed = json.loads(sort_param)
                for s in sort_parsed:
                    selector = s.get("selector")
                    desc = s.get("desc", False)
                    if selector == "attendee_name":
                        sort_list.append("-first_name" if desc else "first_name")
                        sort_list.append("-last_name" if desc else "last_name")
                    elif selector == "total_attendances":
                        sort_list.append("-total_attendances" if desc else "total_attendances")
                    elif selector in ("team__display_name", "team", "team__display_order"):
                        sort_list.append("-team__display_order" if desc else "team__display_order")
            except (ValueError, TypeError):
                pass

        # Grouping
        group_param = request.query_params.get("group")
        group_column = None
        group_desc = False
        if group_param:
            try:
                group_parsed = json.loads(group_param)
                if isinstance(group_parsed, list) and len(group_parsed) > 0 and isinstance(group_parsed[0], dict):
                    group_column = group_parsed[0].get("selector")
                    group_desc = group_parsed[0].get("desc", False)
                    if group_column in ("team__display_name", "team"):
                        group_column = "team__display_name"
                        group_sort = "-team__display_order" if group_desc else "team__display_order"
                        if group_sort in sort_list:
                            sort_list.remove(group_sort)
                        sort_list.insert(0, group_sort)
                    elif group_column in ("character__display_name", "character"):
                        group_column = "character__display_name"
                        group_sort = "-character__display_name" if group_desc else "character__display_name"
                        if group_sort in sort_list:
                            sort_list.remove(group_sort)
                        sort_list.insert(0, group_sort)
                    elif group_column == "attendee_name":
                        group_sort = "-first_name" if group_desc else "first_name"
                        if group_sort in sort_list:
                            sort_list.remove(group_sort)
                        sort_list.insert(0, group_sort)
            except (ValueError, TypeError):
                pass

        # Search
        search_value = request.query_params.get("searchValue")
        if not search_value:
            filter_param = request.query_params.get("filter")
            if filter_param:
                try:
                    filter_parsed = json.loads(filter_param)
                    def extract_search_value(filter_expr):
                        if not filter_expr:
                            return None
                        if isinstance(filter_expr, str):
                            return filter_expr if filter_expr not in ("and", "or", "!") else None
                        if isinstance(filter_expr, list):
                            if len(filter_expr) == 3 and filter_expr[1] == "contains" and isinstance(filter_expr[2], str):
                                return filter_expr[2]
                            for item in filter_expr:
                                val = extract_search_value(item)
                                if val:
                                    return val
                        return None

                    search_value = extract_search_value(filter_parsed)
                except (ValueError, TypeError):
                    pass

        columns = GatheringService.get_roster_gatherings(
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
        )

        _, rows, total_count = RosterService.get_roster_data(
            current_user=request.user,
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
            skip=skip,
            take=take,
            sort_list=sort_list,
            search_value=search_value,
            columns=columns,
        )

        if group_column:
            grouped_data = []
            for key, items in groupby(rows, key=lambda r: r.get(group_column)):
                items_list = list(items)
                grouped_data.append({
                    "key": key,
                    "items": items_list,
                    "count": len(items_list)
                })
            transformed_rows = grouped_data
        else:
            transformed_rows = rows

        serializer = RosterResponseSerializer({
            "totalCount": total_count,
            "columns": columns,
            "rows": transformed_rows,
            "data": transformed_rows,
        })

        return Response(serializer.data)
api_organization_meet_rosters_viewset = ApiOrganizationMeetRostersViewSet
