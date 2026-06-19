import logging
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from attendees.whereabouts.serializers import PlaceSerializer
from attendees.whereabouts.services.coordinates_service import CoordinatesService

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
            top_n = int(request.query_params.get("top", 30))
        except ValueError:
            top_n = 30

        try:
            target_place, neighbors = CoordinatesService.get_nearest_neighbors(pk, top_n)
        except Exception as e:
            logger.error(f"Error fetching nearest neighbors: {e}")
            return Response(
                {"detail": "Error processing request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not target_place:
            return Response(
                {"detail": "No valid coordinates found for the provided ID. Please update the spatial data first."},
                status=status.HTTP_404_NOT_FOUND
            )

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
