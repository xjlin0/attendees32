# Find Neighbors Feature Plan

## Objective
Implement a spatial feature to calculate and display the 30 nearest neighbors based on an Attendee or Folk's linked address. This involves geocoding existing addresses using the Google Maps API, calculating distances using PostGIS, and displaying the results in a DevExtreme popup modal.

## Scope & Impact
*   **Backend**: Create a Geocoding service, a management command for batch processing, and two new DRF APIs (one for triggering geocoding, one for fetching neighbors).
*   **Database**: Utilize existing `latitude` and `longitude` fields on the `address_address` table. Leverage PostGIS for spatial distance calculations (e.g., Euclidean distance or Haversine formula based on coordinates).
*   **Frontend**: Update `attendee_update_view.js` and `attendee_update_view.html` to add a "Find neighbors" link in the Place popup, trigger the geocoding API, and display the results in a new scrollable modal.

## Proposed Solution

### 1. Geocoding Service (`attendees/whereabouts/services/geocoding_service.py`)
*   Create a service class to handle Google Maps API interactions.
*   **Method**: `geocode_address(address_id)`
    *   Fetches the `Address` instance.
    *   If `latitude`/`longitude` are missing, calls Google Maps Geocoding API using `settings.GOOGLE_MAPS_API_KEY`.
    *   Parses the response for coordinates.
    *   Updates the target `Address` and *all* other `Address` records with matching `street_number`, `route`, and `locality_id` to save API calls.

### 2. Management Command (`attendees/whereabouts/management/commands/populate_coordinates.py`)
*   Iterates through all `Address` records where `latitude` OR `longitude` is null.
*   Calls `GeocodingService.geocode_address()` for each.
*   Includes a small sleep interval to respect Google Maps API rate limits.

### 3. APIs
*   **`UpdateSpatialAPIView` (`/whereabouts/api/update_spatial_for/<place_id>/`)**:
    *   Accepts GET or POST (POST preferred for state changes).
    *   Retrieves the `Address` associated with the `Place`.
    *   Calls `GeocodingService.geocode_address()`.
    *   Returns 200 OK (no data required).
*   **`NearestNeighborsAPIView` (`/whereabouts/api/nearest_neighbors_for/<object_id>/`)**:
    *   Accepts an `object_id` (Folk or Attendee UUID).
    *   Identifies the primary coordinates for the given object via its `Place` and `Address` relations.
    *   **Distance Calculation (PostGIS)**: Construct a Django `RawSQL` or an annotated database function that performs a CAST of the `address_address` floating-point fields to PostGIS geography points. Since `ST_DistanceSphere` returns meters, the result must be multiplied by `0.000621371` to convert the distance to **miles**.
        *   **Drafted QuerySet**:
            ```python
            from django.db.models.expressions import RawSQL
            
            # target_lon and target_lat are obtained from the target object's Address
            distance_sql = """
                ST_DistanceSphere(
                    ST_MakePoint(address_address.longitude, address_address.latitude),
                    ST_MakePoint(%s, %s)
                ) * 0.000621371
            """
            
            neighbors = Place.objects.select_related('address').filter(
                address__latitude__isnull=False,
                address__longitude__isnull=False,
            ).annotate(
                distance_miles=RawSQL(distance_sql, (target_lon, target_lat))
            ).exclude(
                id=target_place_id
            ).order_by('distance_miles')[:30]
            ```
    *   Orders the `Place` queryset by the calculated distance, limits to 30 (`?top=30`).
    *   Serializes the data using a modified `PlaceSerializer`.

### 4. Serializer Update (`PlaceSerializer`)
*   Add a `SerializerMethodField` named `attendee_id`.
*   **Query Strategy**:
    *   Check `obj.content_type.model`.
    *   If `'attendee'`, simply return `obj.object_id`.
    *   If `'folk'`, query the related attendees: `FolkAttendee.objects.filter(folk_id=obj.object_id).order_by('display_order').values_list('attendee_id', flat=True).first()`. This efficiently fetches the UUID of the primary attendee linked to that Folk.
*   Add a `distance` field (passed down from the annotated queryset) to handle the `"0.7 miles"` string.

### 5. Frontend (`attendee_update_view.js` & `.html`)
*   **HTML**: Add a DevExtreme Popup container (`<div id="nearest-neighbors-popup"></div>`) in `attendee_update_view.html`.
*   **JS**:
    *   Add `Attendees.datagridUpdate.updateSpatial(placeId)` to call the `update_spatial_for` API asynchronously. Hook this into the Place form initialization (`initPlacePopupDxForm`).
    *   In the Place form, append a `<a href="#" id="find-neighbors-btn">🔎Find neighbors</a>` next to the Google Map link.
    *   On click: Hide the Place popup, show the new Nearest Neighbors popup.
    *   Fetch data from `/whereabouts/api/nearest_neighbors_for/<id>/?top=30`.
    *   Render a list/grid inside the modal, displaying `{address.display_name} - {distance}`, with the name linking to `/persons/attendee/<attendee_id>`.

### 6. Documentation
*   Add `plans/find-neighbors-feature.md` to `docs/index.rst` under the Sphinx `toctree` so the architectural design is published in the local docs server (`http://localhost:7001`).

## Alternatives Considered
*   **PostGIS `PointField` vs. `double precision`**: The existing schema uses standard floats. While PostGIS `ST_DistanceSphere` requires geometry types, we can cast the floats to geography/geometry in a raw query or use standard math formulas in the Django ORM to achieve the same result without altering the `django-address` third-party schema.

## Migration & Rollback
*   Code changes only; no schema migrations required as we are utilizing existing blank fields.
*   Rollback involves reverting the codebase. Geocoded data can remain in the database harmlessly.