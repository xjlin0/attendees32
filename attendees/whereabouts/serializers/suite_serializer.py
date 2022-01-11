from rest_framework import serializers

from attendees.whereabouts.models import Suite


class SuiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suite
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
