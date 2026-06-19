import logging
from django.contrib.auth.decorators import login_required
from django.db.models.expressions import RawSQL
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from attendees.whereabouts.models import Place
from attendees.whereabouts.serializers import PlaceSerializer

logger = logging.getLogger(__name__)


@method_decorator([login_required], name="dispatch")
class NearestNeighborsAPIView(APIView):
    """
    API endpoint to fetch the nearest neighbors based on an Attendee or Folk ID.
    Returns the nearest 30 valid places sorted by distance.
    """

    def get(self, request, pk, format=None):
        logger.info(f"NearestNeighborsAPIView, pk: {pk}")
        try:
            # We look for the specific Place the user clicked on
            target_place = Place.objects.select_related('address').filter(
                pk=pk,
                address__latitude__isnull=False,
                address__longitude__isnull=False
            ).first()
        except Exception as e:
            logger.error(f"Error fetching target place for nearest neighbors: {e}")
            return Response(
                {"detail": "Error processing request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not target_place:
            return Response(
                {"detail": "No valid coordinates found for the provided ID. Please update the spatial data first."},
                status=status.HTTP_404_NOT_FOUND
            )

        target_lat = target_place.address.latitude
        target_lon = target_place.address.longitude

        try:
            top_n = int(request.query_params.get("top", 30))
        except ValueError:
            top_n = 30

        # Construct the PostGIS Distance Query using RawSQL.
        # ST_DistanceSphere returns meters. Multiply by 0.000621371 to get miles.
        distance_sql = """
            ST_DistanceSphere(
                ST_MakePoint(address_address.longitude, address_address.latitude),
                ST_MakePoint(%s, %s)
            ) * 0.000621371
        """

        neighbors = Place.objects.select_related('address', 'content_type').filter(
            address__latitude__isnull=False,
            address__longitude__isnull=False,
        ).annotate(
            distance_miles=RawSQL(distance_sql, (target_lon, target_lat))
        ).exclude(
            id=target_place.id  # Exclude themselves
        ).order_by('distance_miles')[:top_n]

        # Use the updated PlaceSerializer which expects the annotated `distance_miles`
        serializer = PlaceSerializer(neighbors, many=True)
        
        return Response(
            {
                "totalCount": len(serializer.data),
                "data": [{"distance": item.pop("distance"), "place": item} for item in serializer.data]
            },
            status=status.HTTP_200_OK
        )


api_nearest_neighbors_view = NearestNeighborsAPIView.as_view()
