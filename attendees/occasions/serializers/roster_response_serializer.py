from rest_framework import serializers

from .roster_column_serializer import RosterColumnSerializer


class RosterResponseSerializer(serializers.Serializer):
    totalCount = serializers.IntegerField()
    groupCount = serializers.IntegerField(required=False, allow_null=True)
    columns = RosterColumnSerializer(many=True, required=False)
    rows = serializers.JSONField()
    data = serializers.JSONField(required=False)
