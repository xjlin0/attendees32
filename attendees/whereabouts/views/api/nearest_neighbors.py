import logging
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from attendees.whereabouts.serializers import PlaceSerializer
from attendees.whereabouts.services.coordinates_service import CoordinatesService
from attendees.users.authorization.route_guard import SpyGuard

logger = logging.getLogger(__name__)


@method_decorator([login_required], name="dispatch")
class NearestNeighborsAPIView(SpyGuard, APIView):
    """
    API endpoint to fetch the nearest neighbors based on a target Place ID.
    
    Query Parameters:
        take (int): The number of records to return (default: 20).
        skip (int): The number of records to skip for pagination (default: 0).
        meets[] (list of str): Optional. A list of meet slugs. If provided, the response 
                               will be filtered to include ONLY those attendees (or folks containing attendees) 
                               who have participated in ANY of the specified meets (logical OR).
                               
    Returns:
        A JSON object containing the total count and a list of neighbor objects 
        sorted by spherical distance (distance_miles).
    """

    def get(self, request, pk, format=None):
        logger.info(f"NearestNeighborsAPIView, pk: {pk}")
        try:
            take = int(request.query_params.get("take", 20))
        except ValueError:
            take = 20

        try:
            skip = int(request.query_params.get("skip", 0))
        except ValueError:
            skip = 0

        meets = request.query_params.getlist("meets[]", [])
        if not meets:
            meets = request.query_params.getlist("meets", [])

        try:
            target_place, neighbors = CoordinatesService.get_nearest_neighbors(pk, self.request.user.organization, take=take, skip=skip, meets=meets)
        except Exception as e:
            logger.error(f"Error fetching nearest neighbors: {e}")
            return Response(
                {"detail": f"Error fetching nearest neighbors: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not target_place:
            return Response(
                {"detail": "No valid coordinates found for the provided Place Id. Please update the spatial data first."},
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
