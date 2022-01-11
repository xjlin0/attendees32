from attendees.whereabouts.models import Division
from rest_framework import serializers


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = [f.name for f in model._meta.fields if f.name not in ['is_removed']]

