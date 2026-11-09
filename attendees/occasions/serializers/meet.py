from rest_framework import serializers

from attendees.occasions.models import Meet
from attendees.occasions.serializers.meet_list_serializer import MeetListSerializer


class MeetSerializer(serializers.ModelSerializer):
    assembly_name = serializers.CharField()
    schedule_rules = serializers.JSONField(read_only=True)

    class Meta:
        model = Meet
        list_serializer_class = MeetListSerializer
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "assembly_name",
            "schedule_rules",
        ]
