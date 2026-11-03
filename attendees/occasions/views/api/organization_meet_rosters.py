import json
import time
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.services import GatheringService, RosterService
from attendees.occasions.serializers import RosterResponseSerializer
from attendees.persons.models import Utility


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
                    elif selector == "grade":
                        sort_list.append("-grade" if desc else "grade")
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
                    elif group_column in ("character__display_name", "character"):
                        group_column = "character__display_name"
            except (ValueError, TypeError):
                pass

        # Search & Filter
        search_value = request.query_params.get("searchValue")
        filter_param = request.query_params.get("filter")
        extra_filters = Q()
        if filter_param:
            try:
                filter_parsed = json.loads(filter_param)
                extra_filters = RosterService.parse_filter_expr(filter_parsed)
                if not search_value:
                    search_value = RosterService.extract_search_value(filter_parsed)
            except (ValueError, TypeError):
                pass

        if group_column:
            counters = RosterService.get_roster_group_counts(
                organization=current_user_organization,
                meet_slugs=meet_slugs,
                start=start,
                finish=finish,
                group_column=group_column,
                group_desc=group_desc,
                search_value=search_value,
                extra_filters=extra_filters,
                current_user=request.user,
            )
            result = Utility.group_count(group_column, counters)
            result["rows"] = result.get("data", [])
            result["groupCount"] = len(result.get("data", []))
            return Response(result)

        columns = GatheringService.get_roster_gatherings(
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
            current_user=request.user,
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
            extra_filters=extra_filters,
            columns=columns,
        )

        serializer = RosterResponseSerializer({
            "totalCount": total_count,
            "columns": columns,
            "rows": rows,
            "data": rows,
        })

        return Response(serializer.data)
api_organization_meet_rosters_viewset = ApiOrganizationMeetRostersViewSet
