import time

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.persons.services import AttendingService
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
                    elif selector in ("team__display_name", "team"):
                        sort_list.append("-team__display_name" if desc else "team__display_name")
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
                    if isinstance(filter_parsed, list):
                        for item in filter_parsed:
                            if isinstance(item, list) and len(item) == 3 and item[1] == "contains":
                                search_value = item[2]
                                break
                            elif isinstance(item, str) and item not in ("and", "or", "!"):
                                search_value = item
                                break
                except (ValueError, TypeError):
                    pass

        columns, rows, total_count = AttendingService.get_roster_data(
            organization=current_user_organization,
            meet_slugs=meet_slugs,
            start=start,
            finish=finish,
            skip=skip,
            take=take,
            sort_list=sort_list,
            search_value=search_value,
        )

        serializer = RosterResponseSerializer({
            "totalCount": total_count,
            "columns": columns,
            "rows": rows
        })

        return Response(serializer.data)
api_organization_meet_rosters_viewset = ApiOrganizationMeetRostersViewSet
