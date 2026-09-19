from rest_framework import serializers

class RosterColumnSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_name = serializers.CharField()
    start = serializers.DateTimeField()
    meet_id = serializers.IntegerField()

class RosterRowSerializer(serializers.Serializer):
    attending_id = serializers.IntegerField()
    attendee_id = serializers.UUIDField()
    attendee_name = serializers.CharField()
    photo_url = serializers.URLField(allow_null=True, required=False)
    attendances = serializers.JSONField()
    attendingmeets = serializers.JSONField()
    total_attendances = serializers.IntegerField()

class RosterResponseSerializer(serializers.Serializer):
    totalCount = serializers.IntegerField()
    columns = RosterColumnSerializer(many=True)
    rows = RosterRowSerializer(many=True)
