import time

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from attendees.occasions.models import Gathering, Attendance
from attendees.persons.models import Attending


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

        # 1. Query Gatherings (Columns)
        gatherings = Gathering.objects.filter(
            meet__slug__in=meet_slugs,
            meet__assembly__division__organization=current_user_organization,
            start__gte=start,
            finish__lte=finish,
            is_removed=False
        ).order_by('start')

        gathering_list = [
            {
                "id": g.id,
                "display_name": g.display_name,
                "start": g.start.isoformat() if g.start else None
            } 
            for g in gatherings
        ]

        # 2. Prefetch Attendances within the date range
        attendance_prefetch = Prefetch(
            'attendance_set',
            queryset=Attendance.objects.filter(
                gathering__in=gatherings,
                is_removed=False
            ).select_related('category'),
            to_attr='recent_attendances'
        )

        # 3. Query Attendings (Rows)
        attendings_qs = Attending.objects.filter(
            meets__slug__in=meet_slugs,
            is_removed=False
        ).select_related('attendee').prefetch_related(attendance_prefetch).distinct()

        # Pagination
        try:
            skip = int(request.query_params.get("skip", 0))
        except ValueError:
            skip = 0
            
        try:
            take = int(request.query_params.get("take", 40))
        except ValueError:
            take = 40

        total_count = attendings_qs.count()
        attendings_page = attendings_qs[skip: skip + take]

        # 4. In-Memory Pivot
        rows = []
        for attending in attendings_page:
            attendance_map = {}
            actual_attendance_count = 0
            for att in attending.recent_attendances:
                attendance_map[str(att.gathering_id)] = {
                    "attendance_id": att.id,
                    "category_id": att.category_id,
                    "category_name": att.category.display_name,
                }
                if att.category_id != 1:
                    actual_attendance_count += 1

            photo_url = None
            if attending.attendee.photo:
                try:
                    photo_url = attending.attendee.photo.url
                except ValueError:
                    pass
            
            rows.append({
                "attending_id": attending.id,
                "attendee_id": attending.attendee.id,
                "attendee_name": attending.attendee.display_label,
                "photo_url": photo_url,
                "attendances": attendance_map,
                "total_attendances": actual_attendance_count,
            })

        return Response({
            "totalCount": total_count,
            "columns": gathering_list,
            "rows": rows
        })
api_organization_meet_rosters_viewset = ApiOrganizationMeetRostersViewSet
