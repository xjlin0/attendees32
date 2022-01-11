from rest_framework import serializers

from attendees.whereabouts.models import Division


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
