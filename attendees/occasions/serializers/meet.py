from rest_framework import serializers

from attendees.occasions.models import Meet


class MeetSerializer(serializers.ModelSerializer):
    assembly_name = serializers.CharField()
    schedule_rules = serializers.JSONField(read_only=True)

    class Meta:
        model = Meet
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "assembly_name",
            "schedule_rules",
        ]
