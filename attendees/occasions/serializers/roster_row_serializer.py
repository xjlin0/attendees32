from rest_framework import serializers


class RosterRowSerializer(serializers.Serializer):
    attending_id = serializers.IntegerField(allow_null=True, required=False)
    attendee_id = serializers.UUIDField()
    attendee_name = serializers.CharField()
    photo_url = serializers.URLField(allow_null=True, required=False)
    team__display_name = serializers.CharField(allow_null=True, required=False)
    team__display_order = serializers.IntegerField(allow_null=True, required=False)
    character__display_name = serializers.CharField(allow_null=True, required=False)
    contacts = serializers.CharField(allow_null=True, required=False)
    attendances = serializers.JSONField()
    attendingmeets = serializers.JSONField()
    total_attendances = serializers.IntegerField()
