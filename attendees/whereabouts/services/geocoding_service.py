import logging
import requests
from django.conf import settings
from address.models import Address

logger = logging.getLogger(__name__)

class GeocodingService:
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
