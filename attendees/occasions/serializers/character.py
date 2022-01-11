from rest_framework import serializers

from attendees.occasions.models import Character


class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
