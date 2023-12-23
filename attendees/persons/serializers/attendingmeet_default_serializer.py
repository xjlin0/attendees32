from rest_framework import serializers

from attendees.persons.models import AttendingMeet


class AttendingmeetDefaultSerializer(serializers.ModelSerializer):
    # meet__assembly = serializers.IntegerField(read_only=True, source='assembly')  # field name conversion for UI to group directly later
    # meet__assembly__display_order = serializers.IntegerField(read_only=True)
    # registrant_attendee_id = serializers.CharField(read_only=True)
    # attendee_id = serializers.CharField(read_only=True)
    # attending__registration__registrant__infos__names__original = serializers.CharField(read_only=True, source='register_name')
    # attending__attendee = serializers.CharField(read_only=True, source='attendee_name')
    # attending__attendee__infos__fixed__grade = serializers.CharField(read_only=True, source='attendee_grade')

    class Meta:
        model = AttendingMeet
        fields = "__all__"

    def create(self, validated_data):
        """
        Create or update `AttendingMeet` instance, given the validated data.
        """
        print("hi 23 in AttendingmeetDefaultSerializer create, validated_data: ", validated_data)
        attendingmeet_id = self._kwargs["data"].get("id")
        obj, created = AttendingMeet.objects.update_or_create(
            id=attendingmeet_id,
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        """
        Update and return an existing `AttendingMeet` instance, given the validated data.
        """
        print("hi 35 in AttendingmeetDefaultSerializer update, validated_data: ", validated_data)
        if (
            True
        ):  # need validations such as if the assembly matching meet, it's better to validate on UI first
            instance.meet = validated_data.get("meet", instance.meet)
            # instance.meet.assembly = validated_data.get('assembly', instance.meet.assembly)
            instance.meet.save()

        instance.attending = validated_data.get("attending", instance.attending)
        instance.start = validated_data.get("start", instance.start)
        instance.finish = validated_data.get("finish", instance.finish)
        instance.character = validated_data.get("character", instance.character)
        instance.category = validated_data.get("category", instance.category)
        instance.team = validated_data.get("team", instance.team)
        instance.infos = {**instance.infos, **validated_data.get("infos", {})}
        instance.save()
        return instance
