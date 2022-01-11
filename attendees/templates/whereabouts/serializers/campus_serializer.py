from rest_framework import serializers

from attendees.whereabouts.models import Campus


class CampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = [f.name for f in model._meta.fields if f.name not in ['is_removed']]
