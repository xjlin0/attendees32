from rest_framework import serializers

from attendees.whereabouts.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [f.name for f in model._meta.fields if f.name not in ["is_removed"]]
