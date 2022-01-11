from rest_framework import serializers

from attendees.persons.models import Attendee


class AttendeeSerializer(serializers.ModelSerializer):
    parents_notifiers_names = serializers.CharField(read_only=True)
    self_email_addresses = serializers.CharField(read_only=True)
    caregiver_email_addresses = serializers.CharField(read_only=True)
    self_phone_numbers = serializers.CharField(read_only=True)
    caregiver_phone_numbers = serializers.CharField(read_only=True)

    class Meta:
        model = Attendee
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "display_label",
            "division_label",
            "parents_notifiers_names",
            "self_email_addresses",
            "caregiver_email_addresses",
            "self_phone_numbers",
            "caregiver_phone_numbers",
        ]
