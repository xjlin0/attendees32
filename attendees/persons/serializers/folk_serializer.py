from rest_framework import serializers

from attendees.persons.models import Attendee, Folk, FolkAttendee, Relation, Utility
from attendees.whereabouts.serializers import PlaceSerializer


class FolkSerializer(serializers.ModelSerializer):
    places = PlaceSerializer(many=True, read_only=True)

    class Meta:
        model = Folk
        fields = "__all__"

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
