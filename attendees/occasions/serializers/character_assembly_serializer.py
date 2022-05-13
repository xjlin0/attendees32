from rest_framework import serializers

from attendees.occasions.models import Character


class CharacterAssemblySerializer(serializers.ModelSerializer):
    assembly_name = serializers.CharField()

    class Meta:
        model = Character
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "assembly_name",
        ]
