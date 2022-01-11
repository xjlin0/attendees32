from pathlib import Path

from rest_framework import serializers

from attendees.persons.models import Attendee
from attendees.persons.serializers import FolkAttendeeSerializer
from attendees.whereabouts.serializers import PlaceSerializer


class AttendeeMinimalSerializer(serializers.ModelSerializer):
    places = PlaceSerializer(many=True, read_only=True)
    folkattendee_set = FolkAttendeeSerializer(read_only=True, many=True)
    photo = serializers.ImageField(
        use_url=True, required=False
    )  # trying DevExtreme dxFileUploader https://supportcenter.devexpress.com/ticket/details/t404408
    photo_path = serializers.SerializerMethodField(required=False, read_only=True)
    attendingmeets = serializers.JSONField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(
        many=False, read_only=True
    )  # For MVP, Admin UI can handle this use case. Todo: when non admins start to use app, admin need to edit this on UI
    organization_slug = serializers.CharField(read_only=True)

    def get_photo_path(self, obj):
        return obj.photo.url if obj.photo else ""

    class Meta:
        model = Attendee
        # fields = '__all__'
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "organization_slug",
            "attendingmeets",
            # 'display_label',
            # 'division_label',
            # 'parents_notifiers_names',
            "folkattendee_set",
            "photo_path",
            # 'caregiver_email_addresses',
            "places",
        ]

    def create(self, validated_data):
        """
        Create and return a new `Attendee` instance, given the validated data.
        """

        return Attendee.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `AttendingMeet` instance, given the validated data.

        """
        deleting_photo = self._kwargs["data"].get("photo-clear", None)

        if instance:
            if deleting_photo or validated_data.get("photo", None):
                old_photo = instance.photo
                if old_photo:
                    old_file = Path(old_photo.path)
                    old_file.unlink(missing_ok=True)
                if deleting_photo:
                    validated_data["photo"] = None

            obj, created = Attendee.objects.update_or_create(
                id=instance.id,
                defaults=validated_data,
            )

        return obj
