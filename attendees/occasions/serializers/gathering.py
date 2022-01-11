from rest_framework import serializers

from attendees.occasions.models import Gathering


class GatheringSerializer(serializers.ModelSerializer):
    site = serializers.CharField(read_only=True)
    gathering_label = serializers.CharField(read_only=True)

    class Meta:
        model = Gathering
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "gathering_label",
            "site",
        ]

    def create(self, validated_data):
        print("hi 17 here is validated_data: ")
        print(validated_data)
        obj, created = Gathering.objects.update_or_create(
            id=None,
            defaults=validated_data,
        )

        return obj

    def update(self, instance, validated_data):
        """
        Update and return an existing `Gathering` instance, given the validated data.

        """
        print("hi 30 here is instance: ")
        print(instance)
        print("hi 31 here is validated_data: ")
        print(validated_data)
        obj, created = Gathering.objects.update_or_create(
            id=instance.id,
            defaults=validated_data,
        )

        return obj
