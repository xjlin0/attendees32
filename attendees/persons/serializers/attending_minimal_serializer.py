from rest_framework import serializers

from attendees.persons.models import Attending, Registration
from attendees.persons.serializers import RegistrationSerializer


class AttendingMinimalSerializer(serializers.ModelSerializer):
    attending_label = serializers.CharField(read_only=True)
    registration = RegistrationSerializer(
        required=False, allow_null=True
    )  # allow_null needed for attendings without registration

    class Meta:
        model = Attending
        fields = (
            "id",
            "registration",
            "attending_label",
            "category",
            "infos",
        )  # It is critical not to have attendee in the fields, to let perform_create set it

    def create(self, validated_data):
        """
        Create or update `Attending` instance, given the validated data.
        """

        if "registration" in validated_data:
            registration_data = validated_data.pop("registration")
            filters = {
                'defaults': registration_data,
            }
            assembly = registration_data.get('assembly')
            registrant = registration_data.get('registrant')

            if assembly:
                filters['assembly'] = assembly
            if registrant:
                filters['registrant'] = registrant
            registration, created = Registration.objects.update_or_create(**filters)
            validated_data["registration"] = registration
        obj, created = Attending.objects.update_or_create(
            id=None,
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        """
        Update and return an existing `Attending` instance, given the validated data.

        """
        if "registration" in validated_data:
            registration_data = validated_data.pop("registration")
            registration, created = Registration.objects.update_or_create(
                id=instance.registration.id if instance.registration else None,
                defaults=registration_data,
            )
            validated_data["registration"] = registration

        obj, created = Attending.objects.update_or_create(
            id=instance.id,
            defaults=validated_data,
        )

        return obj
