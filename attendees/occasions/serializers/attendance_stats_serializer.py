from rest_framework import serializers

from attendees.occasions.models import Attendance


class AttendanceStatsSerializer(serializers.ModelSerializer):
    characters = serializers.CharField(read_only=True)
    teams = serializers.CharField(read_only=True)
    attending__attendee__infos__names__original = serializers.CharField(read_only=True)
    attending__attendee = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)
    attending__registration__registrant_id = serializers.CharField(read_only=True)
    attending_name = serializers.CharField(read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "characters",
            "teams",
            "attending__attendee__infos__names__original",
            "attending__attendee",
            "count",
            "attending__registration__registrant_id",
            "attending_name",
        ]
