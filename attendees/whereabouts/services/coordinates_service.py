import logging
import requests
from django.conf import settings
from address.models import Address

from django.db.models.expressions import RawSQL
from attendees.whereabouts.models import Place

logger = logging.getLogger(__name__)


class CoordinatesService:
    @staticmethod
    def get_nearest_neighbors(place_id, user_organization, top_n=30):
        """
        Fetches the nearest neighbors based on a Place ID.
        Returns a tuple: (target_place, neighbors_queryset)
        """
        target_place = Place.objects.select_related('address').filter(
            pk=place_id,
            organization=user_organization,
            address__latitude__isnull=False,
            address__longitude__isnull=False
        ).first()

        if not target_place:
            return None, []

        target_lat = target_place.address.latitude
        target_lon = target_place.address.longitude

        distance_sql = """
            ST_DistanceSphere(
                ST_MakePoint(address_address.longitude, address_address.latitude),
                ST_MakePoint(%s, %s)
            ) * 0.000621371
        """

        azimuth_sql = """
            ST_Azimuth(
                ST_MakePoint(%s, %s),
                ST_MakePoint(address_address.longitude, address_address.latitude)
            )
        """

        neighbors = Place.objects.select_related('address', 'content_type').filter(
            organization=user_organization,
            address__latitude__isnull=False,
            address__longitude__isnull=False,
        ).annotate(
            distance_miles=RawSQL(distance_sql, (target_lon, target_lat)),
            azimuth=RawSQL(azimuth_sql, (target_lon, target_lat))
        ).exclude(
            id=target_place.id
        ).order_by('distance_miles')[:top_n]

        return target_place, neighbors

    @staticmethod
    def geocode_address(address_id):
        """
        Fetches coordinates for a given address ID from Google Maps API.
        If successful, updates the target address and all matching sibling addresses
        (same street_number, route, and locality) to minimize API usage.
        """
        if not settings.GOOGLE_MAPS_API_KEY:
            logger.warning("GOOGLE_MAPS_API_KEY is not set. Geocoding skipped.")
            return False

        try:
            target_address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            logger.error(f"Address with id {address_id} does not exist.")
            return False

        if target_address.latitude and target_address.longitude:
            logger.info(f"Address {address_id} already has coordinates. Skipping.")
            return True

        # Construct the search string. Ensure we have the necessary parts.
        search_parts = []
        if target_address.street_number:
            search_parts.append(target_address.street_number)
        if target_address.route:
            search_parts.append(target_address.route)
        if target_address.locality:
            search_parts.append(target_address.locality.name)
            if target_address.locality.state:
                search_parts.append(target_address.locality.state.name)
                if target_address.locality.state.country:
                    search_parts.append(target_address.locality.state.country.name)

        if not search_parts:
            logger.warning(f"Address {address_id} has insufficient data for geocoding.")
            return False

        search_query = ", ".join(search_parts)
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": search_query,
            "key": settings.GOOGLE_MAPS_API_KEY
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                lat = location.get("lat")
                lng = location.get("lng")

                if lat is not None and lng is not None:
                    # Update target and all siblings
                    Address.objects.filter(
                        street_number=target_address.street_number,
                        route=target_address.route,
                        locality=target_address.locality
                    ).update(latitude=lat, longitude=lng)
                    
                    logger.info(f"Successfully geocoded Address {address_id} and siblings to ({lat}, {lng})")
                    return True
            else:
                logger.warning(f"Geocoding failed for Address {address_id}. API Response: {data.get('status')}")
                return False

        except requests.RequestException as e:
            logger.error(f"Error calling Google Maps API for Address {address_id}: {e}")
            return False
