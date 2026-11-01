from rest_framework import serializers

from .roster_column_serializer import RosterColumnSerializer


class RosterResponseSerializer(serializers.Serializer):
    totalCount = serializers.IntegerField()
    columns = RosterColumnSerializer(many=True, required=False)
    rows = serializers.JSONField()
    data = serializers.JSONField(required=False)
