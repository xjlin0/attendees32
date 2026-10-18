from rest_framework import serializers

class RosterColumnSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True, required=False)
    display_name = serializers.CharField()
    start = serializers.DateTimeField()
    meet_id = serializers.IntegerField()
    meet_display_name = serializers.CharField(allow_blank=True, required=False, default="")

class RosterRowSerializer(serializers.Serializer):
    attending_id = serializers.IntegerField(allow_null=True, required=False)
    attendee_id = serializers.UUIDField()
    attendee_name = serializers.CharField()
    photo_url = serializers.URLField(allow_null=True, required=False)
    team__display_name = serializers.CharField(allow_null=True, required=False)
    team__display_order = serializers.IntegerField(allow_null=True, required=False)
    contacts = serializers.CharField(allow_null=True, required=False)
    attendances = serializers.JSONField()
    attendingmeets = serializers.JSONField()
    total_attendances = serializers.IntegerField()

class RosterResponseSerializer(serializers.Serializer):
    totalCount = serializers.IntegerField()
    columns = RosterColumnSerializer(many=True, required=False)
    rows = serializers.JSONField()
    data = serializers.JSONField(required=False)
