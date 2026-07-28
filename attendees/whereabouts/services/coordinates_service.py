import copy
import logging
import requests
from django.conf import settings
from address.models import Address

from django.contrib.contenttypes.models import ContentType
from attendees.persons.models import Attendee, Folk, AttendingMeet, FolkAttendee, Utility
from django.db.models.functions import Cast
from django.db import models
from django.db.models import Q

from django.db.models.expressions import RawSQL
from attendees.whereabouts.models import Place

logger = logging.getLogger(__name__)


class CoordinatesService:
    @staticmethod
    def get_nearest_neighbors(place_id, user_organization, take=20, skip=0, meets=None):
        """
        Fetches the nearest neighbors based on a target Place ID.
        
        Args:
            place_id: The primary key of the target Place.
            user_organization: The organization of the current user.
            take (int): Pagination limit.
            skip (int): Pagination offset.
            meets (list of str): Optional. A list of meet slugs. If provided, filters neighbors 
                                 so that the results only include attendees (or folks containing attendees) 
                                 who have attended AT LEAST ONE of the specified meets (Logical OR).
        
        Returns:
            A tuple: (target_place, neighbors_list)
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
        )

        attendee_ct = ContentType.objects.get_for_model(Attendee)
        folk_ct = ContentType.objects.get_for_model(Folk)

        now_dt = Utility.now_with_timezone()
        now_date = now_dt.date()

        active_attendee_ids = None
        if meets:
            active_attendee_ids = set(
                AttendingMeet.objects.filter(
                    meet__slug__in=meets,
                    is_removed=False,
                    finish__gte=now_dt,
                    attending__is_removed=False,
                    attending__attendee__is_removed=False,
                ).values_list("attending__attendee_id", flat=True)
            )

            valid_folk_ids = set(
                FolkAttendee.objects.filter(
                    attendee_id__in=active_attendee_ids,
                    is_removed=False,
                    folk__is_removed=False,
                ).filter(
                    Q(finish__isnull=True) | Q(finish__gte=now_date)
                ).values_list('folk_id', flat=True)
            )

            attendee_str_ids = [str(aid) for aid in active_attendee_ids]
            folk_str_ids = [str(fid) for fid in valid_folk_ids]

            q_attendee = Q(content_type=attendee_ct, object_id__in=attendee_str_ids)
            q_folk = Q(content_type=folk_ct, object_id__in=folk_str_ids)
            neighbors = neighbors.filter(q_attendee | q_folk)

        ordered_places = list(neighbors.order_by('distance_miles'))

        attendee_object_ids = [str(p.object_id) for p in ordered_places if p.content_type_id == attendee_ct.id and p.object_id]
        folk_object_ids = [str(p.object_id) for p in ordered_places if p.content_type_id == folk_ct.id and p.object_id]

        attendees_map = {}
        if attendee_object_ids:
            for att in Attendee.objects.select_related('division').filter(id__in=attendee_object_ids, is_removed=False):
                acronym = att.division.infos.get('acronym', '') if att.division and isinstance(att.division.infos, dict) else ''
                name_orig = att.infos.get('names', {}).get('original', '') if isinstance(att.infos, dict) else ''
                attendees_map[str(att.id)] = f"{acronym} {name_orig}".strip()

        folk_attendees_map = {}
        if folk_object_ids:
            fa_query = FolkAttendee.objects.select_related('attendee', 'attendee__division').filter(
                Q(finish__isnull=True) | Q(finish__gte=now_date),
                folk_id__in=folk_object_ids,
                is_removed=False,
                attendee__is_removed=False,
            ).order_by('display_order')

            if active_attendee_ids is not None:
                fa_query = fa_query.filter(attendee_id__in=active_attendee_ids)

            for fa in fa_query:
                att = fa.attendee
                acronym = att.division.infos.get('acronym', '') if att.division and isinstance(att.division.infos, dict) else ''
                name_orig = att.infos.get('names', {}).get('original', '') if isinstance(att.infos, dict) else ''
                display_name = f"{acronym} {name_orig}".strip()
                folk_attendees_map.setdefault(str(fa.folk_id), []).append((str(att.id), display_name))

        expanded_list = []
        active_attendee_str_ids = {str(aid) for aid in active_attendee_ids} if active_attendee_ids is not None else None

        for p in ordered_places:
            if p.content_type_id == attendee_ct.id:
                if p.object_id:
                    obj_id_str = str(p.object_id)
                    if obj_id_str in attendees_map:
                        if active_attendee_str_ids is None or obj_id_str in active_attendee_str_ids:
                            p.target_attendee_id = obj_id_str
                            p.target_attendee_name = attendees_map[obj_id_str]
                            expanded_list.append(p)
            elif p.content_type_id == folk_ct.id:
                if p.object_id:
                    obj_id_str = str(p.object_id)
                    fa_list = folk_attendees_map.get(obj_id_str, [])
                    for att_id_str, att_name in fa_list:
                        cloned_p = copy.copy(p)
                        cloned_p.target_attendee_id = att_id_str
                        cloned_p.target_attendee_name = att_name
                        expanded_list.append(cloned_p)
            else:
                if not meets:
                    expanded_list.append(p)

        return target_place, expanded_list[skip : skip + take]

    @staticmethod
    def geocode_address(address_id, return_details=False):
        """
        Fetches coordinates for a given address ID from Google Maps API.
        If successful, updates the target address and all matching sibling addresses
        (same street_number, route, and locality) to minimize API usage.
        """
        def result(success, message):
            return (success, message) if return_details else success

        if not settings.GOOGLE_MAPS_API_KEY:
            msg = "GOOGLE_MAPS_API_KEY is not set."
            logger.warning(f"{msg} Geocoding skipped.")
            return result(False, msg)

        try:
            target_address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            msg = f"Address with id {address_id} does not exist."
            logger.error(msg)
            return result(False, msg)

        if target_address.latitude and target_address.longitude:
            msg = "Already has coordinates."
            logger.info(f"Address {address_id} already has coordinates. Skipping.")
            return result(True, msg)

        if not target_address.street_number or not target_address.route:
            msg = "Missing street_number or route."
            logger.warning(f"Address {address_id} is missing street_number or route. Geocoding skipped.")
            return result(False, msg)

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
            msg = "Insufficient data for geocoding."
            logger.warning(f"Address {address_id} has insufficient data for geocoding.")
            return result(False, msg)

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
            status_code = data.get("status")

            if status_code == "OK" and data.get("results"):
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
                    
                    msg = f"Geocoded to ({lat}, {lng})"
                    logger.info(f"Successfully geocoded Address {address_id} and siblings to ({lat}, {lng})")
                    return result(True, msg)
                else:
                    msg = "API Status OK but lat/lng missing."
                    logger.warning(f"Geocoding failed for Address {address_id}. {msg}")
                    return result(False, msg)
            else:
                error_msg = data.get("error_message", "")
                reason_str = f"{status_code}" + (f" - {error_msg}" if error_msg else "")
                logger.warning(f"Geocoding failed for Address {address_id}. API Response: {reason_str}")
                return result(False, f"API Response: {reason_str}")

        except requests.RequestException as e:
            msg = f"Request error: {e}"
            logger.error(f"Error calling Google Maps API for Address {address_id}: {e}")
            return result(False, msg)
