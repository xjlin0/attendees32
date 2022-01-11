from rest_framework import serializers

from attendees.whereabouts.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
