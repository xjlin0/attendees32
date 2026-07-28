from address.models import Address, Locality, State
from django.db.models import Q
from rest_framework import serializers

from attendees.persons.models import Attendee, FolkAttendee, Utility
from attendees.whereabouts.models import Place
from attendees.whereabouts.serializers import AddressSerializer


class PlaceSerializer(serializers.ModelSerializer):
    """
    Generic relation: https://www.django-rest-framework.org/api-guide/relations/#generic-relationships
    """

    street = serializers.CharField(read_only=True)
    address = AddressSerializer(required=False)
    distance = serializers.SerializerMethodField()
    attendee_id = serializers.SerializerMethodField()
    attendee_name = serializers.SerializerMethodField()

    class Meta:
        model = Place
        # fields = '__all__'
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "street",
            "address",
            "distance",
            "attendee_id",
            "attendee_name",
        ]

    def get_distance(self, obj):
        if hasattr(obj, 'distance_miles') and obj.distance_miles is not None:
            direction = ""
            if hasattr(obj, 'azimuth') and obj.azimuth is not None:
                import math
                degrees = math.degrees(obj.azimuth)
                dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
                ix = round(degrees / 45) % 8
                direction = f" {dirs[ix]}"
            return f"{obj.distance_miles:.1f} miles{direction}"
        return None

    def get_attendee_id(self, obj):
        target_id = getattr(obj, '__dict__', {}).get('target_attendee_id')
        if target_id is not None:
            return str(target_id)
        if obj.content_type.model == 'attendee':
            return str(obj.object_id)
        elif obj.content_type.model == 'folk':
            now_date = Utility.now_with_timezone().date()
            try:
                fa = FolkAttendee.objects.filter(
                    Q(finish__isnull=True) | Q(finish__gte=now_date),
                    folk_id=obj.object_id,
                    is_removed=False,
                    attendee__is_removed=False,
                ).order_by('display_order').first()
                return str(fa.attendee_id) if fa else None
            except Exception:
                return None
        return None

    def get_attendee_name(self, obj):
        target_name = getattr(obj, '__dict__', {}).get('target_attendee_name')
        if target_name is not None:
            return target_name
        if obj.content_type.model == 'attendee':
            try:
                att = Attendee.objects.select_related('division').filter(pk=obj.object_id, is_removed=False).first()
            except Exception:
                return None
            if not att:
                return None
            acronym = att.division.infos.get('acronym', '') if att.division and isinstance(att.division.infos, dict) else ''
            name_orig = att.infos.get('names', {}).get('original', '') if isinstance(att.infos, dict) else ''
            return f"{acronym} {name_orig}".strip()
        elif obj.content_type.model == 'folk':
            now_date = Utility.now_with_timezone().date()
            try:
                fa = FolkAttendee.objects.select_related('attendee', 'attendee__division').filter(
                    Q(finish__isnull=True) | Q(finish__gte=now_date),
                    folk_id=obj.object_id,
                    is_removed=False,
                    attendee__is_removed=False,
                ).order_by('display_order').first()
            except Exception:
                return None
            if not fa or not fa.attendee:
                return None
            att = fa.attendee
            acronym = att.division.infos.get('acronym', '') if att.division and isinstance(att.division.infos, dict) else ''
            name_orig = att.infos.get('names', {}).get('original', '') if isinstance(att.infos, dict) else ''
            return f"{acronym} {name_orig}".strip()
        return None

    def _get_subject_name(self, validated_data, instance=None):
        ct = validated_data.get('content_type')
        if not ct and instance:
            ct = instance.content_type

        obj_id = validated_data.get('object_id')
        if not obj_id and instance:
            obj_id = instance.object_id

        if not ct or not obj_id:
            return ""

        if ct.model == 'attendee':
            from attendees.persons.models import Attendee
            attendee = Attendee.objects.filter(pk=obj_id).first()
            if attendee and attendee.infos and 'names' in attendee.infos and 'original' in attendee.infos['names']:
                return attendee.infos['names']['original']
        elif ct.model == 'folk':
            from attendees.persons.models import Folk
            folk = Folk.objects.filter(pk=obj_id).first()
            if folk:
                return folk.display_name

        return ""

    def _handle_address_update_or_fork(self, place_data, validated_data, instance=None, is_update=False):
        address_data = place_data.get("address")
        if not address_data:
            return None

        address_id = address_data.get("id")

        # 1. Resolve locality safely
        new_city = address_data.get("city")
        new_zip = address_data.get("postal_code")
        state_id = address_data.get("state_id")

        locality = None
        if state_id:
            new_state = State.objects.filter(pk=state_id).first()
            if new_state and new_city:
                locality, _ = Locality.objects.update_or_create(
                    name=new_city,
                    postal_code=new_zip,
                    state=new_state,
                    defaults={
                        "name": new_city,
                        "postal_code": new_zip,
                        "state": new_state,
                    },
                )

        # 2. Extract valid address fields
        clean_address_data = {}
        valid_fields = ['street_number', 'route', 'extra', 'name', 'type', 'hash', 'raw', 'formatted', 'latitude', 'longitude']
        for field in valid_fields:
            if field in address_data:
                clean_address_data[field] = address_data[field]
        if locality:
            clean_address_data["locality"] = locality

        place_display_name = validated_data.get("display_name") or place_data.get("display_name")
        if not place_display_name and instance:
            place_display_name = instance.display_name
        if not place_display_name:
            place_display_name = "main"

        subject_name = self._get_subject_name(validated_data, instance)

        generated_name = f"{subject_name} {place_display_name} address".strip()
        if generated_name:
            clean_address_data["name"] = generated_name[:40]

        # 3. If address_id is provided, decide Mutate vs Fork
        if address_id:
            try:
                old_address = Address.objects.get(id=address_id)
            except Address.DoesNotExist:
                old_address = None

            if old_address:
                # Compare fields to see if anything actually changed
                is_different = False
                for k, v in clean_address_data.items():
                    if getattr(old_address, k) != v:
                        is_different = True
                        break

                if not is_different:
                    return old_address # No changes, return the existing one safely

                # Changes detected!
                if is_update:
                    usage_count = Place.objects.filter(address=old_address).count()
                    if usage_count <= 1:
                        # Safe to mutate
                        for k, v in clean_address_data.items():
                            setattr(old_address, k, v)
                        old_address.save()
                        return old_address

        # 4. Fork / Create new address
        # Remove any empty/None fields for a cleaner get_or_create/filter
        search_kwargs = {k: v for k, v in clean_address_data.items() if v is not None}

        # We can't rely on getting an exact match for float lat/long sometimes, 
        # but for simplicity, we just create a new one.
        # Alternatively, try to find an existing one first to deduplicate
        if search_kwargs:
            existing_address = Address.objects.filter(**search_kwargs).first()
            if existing_address:
                return existing_address

        return Address.objects.create(**clean_address_data)

    def create(self, validated_data):
        """
        Create or update `Place` instance, given the validated data.
        """
        place_data = self._kwargs.get("data", {})
        place_id = place_data.get("id")
        address_data = place_data.get("address")

        if address_data:
            if "new_address" in address_data:
                # Bypass DRF model validations
                new_address_data = address_data.get("new_address", {})
                if "address" in validated_data:
                    del validated_data["address"]
                place, _ = Place.objects.update_or_create(
                    id=place_id,
                    defaults=validated_data,
                )
                place.address = new_address_data
                place.save()
                return place
            else:
                address = self._handle_address_update_or_fork(place_data, validated_data, is_update=False)
                validated_data["address"] = address

        place, _ = Place.objects.update_or_create(
            id=place_id,
            defaults=validated_data,
        )

        return place

    def update(self, instance, validated_data):
        """
        Update and return an existing `Place` instance, given the validated data.
        """
        place_data = self._kwargs.get("data", {})
        address_data = place_data.get("address")

        if address_data:
            if "new_address" in address_data:
                # Bypass DRF model validations
                new_address_data = address_data.get("new_address", {})
                if "address" in validated_data:
                    del validated_data["address"]
                place, _ = Place.objects.update_or_create(
                    id=instance.id,
                    defaults=validated_data,
                )
                place.address = new_address_data
                place.save()
                return place
            else:
                address = self._handle_address_update_or_fork(place_data, validated_data, instance=instance, is_update=True)
                validated_data["address"] = address

        place, _ = Place.objects.update_or_create(
            id=instance.id,
            defaults=validated_data,
        )

        return place
