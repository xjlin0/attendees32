from rest_framework import serializers


class RosterColumnSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True, required=False)
    display_name = serializers.CharField()
    start = serializers.DateTimeField()
    finish = serializers.DateTimeField(allow_null=True, required=False)
    meet_id = serializers.IntegerField()
    meet_display_name = serializers.CharField(allow_blank=True, required=False, default="")
    attendances_count = serializers.IntegerField(default=0, required=False)
    enrolled_count = serializers.IntegerField(default=0, required=False)
