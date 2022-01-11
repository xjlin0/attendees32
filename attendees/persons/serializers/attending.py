from rest_framework import serializers

from attendees.persons.models import Attending

from .attendee import AttendeeSerializer


class AttendingSerializer(serializers.ModelSerializer):
    meets_info = serializers.SerializerMethodField()
    attendee = AttendeeSerializer(many=False, read_only=True)

    def get_meets_info(self, obj):
        return {
            am.meet.slug: am.character.display_name
            for am in obj.attendingmeet_set.all()
        }

    class Meta:
        model = Attending
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "attending_label",
            "meets_info",
            "attendee",
        ]
