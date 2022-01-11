from rest_framework import serializers

from attendees.persons.models import Relation


class RelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Relation
        fields = "__all__"
