import logging
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from attendees.whereabouts.models import Place
from attendees.whereabouts.services.geocoding_service import GeocodingService

logger = logging.getLogger(__name__)


@method_decorator([login_required], name="dispatch")
class UpdateSpatialAPIView(APIView):
    """
    API endpoint to trigger geocoding for a specific Place's Address.
    """

    def post(self, request, pk, format=None):
        logger.info(f"UpdateSpatialAPIView: {pk}")
        try:
            place = Place.objects.select_related('address').get(pk=pk)
        except Place.DoesNotExist:
            return Response(
                {"detail": "Place not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not place.address:
            return Response(
                {"detail": "Place has no associated address."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # The service handles checking if it already has coordinates,
        # fetching from Google Maps, and updating the database.
        success = GeocodingService.geocode_address(place.address.id)

        if success:
            return Response(
                {"detail": "Address coordinates updated successfully."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Failed to update coordinates or they already exist."},
                status=status.HTTP_200_OK  # 200 OK because the action completed (even if skipped/failed silently)
            )


api_update_spatial_view = UpdateSpatialAPIView.as_view()
