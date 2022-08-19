from rest_framework import serializers

from attendees.occasions.models import Attendance


class AttendanceEtcSerializer(serializers.ModelSerializer):
    gathering__meet__assembly = serializers.IntegerField(read_only=True, source='assembly')
    gathering__meet = serializers.IntegerField(read_only=True, source='meet')
    gathering__display_name = serializers.CharField(read_only=True, source='gathering_name')
    attending__attendee__infos__names__original = serializers.CharField(read_only=True, source='attending_name')
    photo = serializers.CharField(read_only=True)

    class Meta:
        model = Attendance
        fields = "__all__"

    def create(self, validated_data):
        """
        Create or update `AttendingMeet` instance, given the validated data.
        """
        attendance_id = self._kwargs["data"].get("id")
        obj, created = Attendance.objects.update_or_create(
            id=attendance_id,
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        """
        Update and return an existing `AttendingMeet` instance, given the validated data.

        """

        # if (
        #     True
        # ):  # need validations such as if the assembly matching meet, it's better to validate on UI first
            # instance.meet = validated_data.get("meet", instance.meet)
            # instance.meet.assembly = validated_data.get('assembly', instance.meet.assembly)
            # instance.meet.save()
        instance.gathering = validated_data.get("gathering", instance.gathering)
        instance.attending = validated_data.get("attending", instance.attending)
        instance.start = validated_data.get("start", instance.start)
        instance.finish = validated_data.get("finish", instance.finish)
        instance.character = validated_data.get("character", instance.character)
        instance.category = validated_data.get("category", instance.category)
        instance.team = validated_data.get("team", instance.team)
        instance.infos = {**instance.infos, **validated_data.get("infos", {})}
        instance.save()
        return instance
