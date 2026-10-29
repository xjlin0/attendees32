from django.db.models import Q
from rest_framework import serializers

from attendees.persons.models import Attendee, Folk, FolkAttendee, Relation, Utility
from attendees.whereabouts.serializers import PlaceSerializer


class FolkSerializer(serializers.ModelSerializer):
    places = PlaceSerializer(many=True, read_only=True)

    class Meta:
        model = Folk
        fields = "__all__"

    def to_representation(self, instance):
        places = (
            instance._prefetched_objects_cache.get("places")
            if hasattr(instance, "_prefetched_objects_cache")
            else None
        )
        if places is not None or hasattr(instance, "places"):
            primary_id = None
            primary_name = None

            if (
                hasattr(instance, "_prefetched_objects_cache")
                and "folkattendee_set" in instance._prefetched_objects_cache
            ):
                active_fas = instance.folkattendee_set.all()
                primary_fa = active_fas[0] if active_fas else None
            else:
                now_date = Utility.now_with_timezone().date()
                primary_fa = FolkAttendee.objects.filter(
                    Q(finish__isnull=True) | Q(finish__gte=now_date),
                    folk_id=instance.id,
                    is_removed=False,
                    attendee__is_removed=False,
                ).select_related("attendee__division").order_by("display_order").first()

            if primary_fa and primary_fa.attendee:
                att = primary_fa.attendee
                acronym = (
                    att.division.infos.get("acronym", "")
                    if att.division and isinstance(att.division.infos, dict)
                    else ""
                )
                name_orig = (
                    att.infos.get("names", {}).get("original", "")
                    if isinstance(att.infos, dict)
                    else ""
                )
                primary_name = f"{acronym} {name_orig}".strip()
                primary_id = str(primary_fa.attendee_id)

            target_places = places if places is not None else instance.places.all()
            for place in target_places:
                if (
                    getattr(place, "__dict__", {}).get("target_attendee_id") is None
                    and getattr(place.content_type, "model", None) == "folk"
                ):
                    place.target_attendee_id = primary_id or ""
                    place.target_attendee_name = primary_name or ""

        return super().to_representation(instance)

    def create(self, validated_data):
        """
        Create or update `Family` instance, given the validated data.
        """
        raw_data = self._kwargs.get("data", {})
        family_id = raw_data.get("id")

        folk, folk_created = Folk.objects.update_or_create(
            id=family_id,
            defaults=validated_data,
        )

        if folk_created:
            for attendee_id in raw_data.get("attendees", []):
                unspecified_role = Relation.objects.filter(title="unspecified").first
                attendee = Attendee.objects.get(pk=attendee_id)
                FolkAttendee.objects.update_or_create(
                    attendee=attendee,
                    folk=folk,
                    defaults={
                        "attendee": attendee,
                        "folk": folk,
                        "role": unspecified_role,
                        "start": Utility.now_with_timezone(),
                    },
                )

        return folk

    def update(self, instance, validated_data):
        """
        Update and return an existing `Family` instance, given the validated data.

        """

        obj, created = Folk.objects.update_or_create(
            id=instance.id,
            defaults=validated_data,
        )

        return obj
