from rest_framework import serializers

from attendees.occasions.models import Assembly


class AssemblySerializer(serializers.ModelSerializer):
    division_assembly_name = serializers.CharField()

    class Meta:
        model = Assembly
        fields = "__all__"
