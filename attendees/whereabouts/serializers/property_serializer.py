from rest_framework import serializers

from attendees.whereabouts.models import Property


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
