import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.persons.services import AttendeeService
from attendees.occasions.serializers.roster_serializer import RosterResponseSerializer


@method_decorator([login_required], name="dispatch")
class ApiOrganizationMeetRostersViewSet(viewsets.ViewSet):
    """
    API endpoint that returns pivoted roster data (gatherings as columns, attendees as rows).
    """

    def list(self, request, *args, **kwargs):
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
            import json
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
            import json
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
                import json
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

        columns, rows, total_count = AttendeeService.get_roster_data(
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
            skip=skip,
            take=take,
            sort_list=sort_list,
            search_value=search_value,
        )

        from itertools import groupby
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
