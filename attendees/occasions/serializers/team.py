from rest_framework import serializers

from attendees.occasions.models import Team


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
