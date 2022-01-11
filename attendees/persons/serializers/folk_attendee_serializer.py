from rest_framework import serializers

from attendees.persons.models import Folk, FolkAttendee
from attendees.persons.serializers import FolkSerializer


class FolkAttendeeSerializer(serializers.ModelSerializer):
    folk = FolkSerializer(many=False)
    # attendee = AttendeeSerializer(many=False)

    class Meta:
        model = FolkAttendee
        fields = "__all__"
        # fields = [f.name for f in model._meta.fields if f.name not in ['is_removed']] + [
        #     'family',
        # ]

    def create(self, validated_data):
        """
        Create or update `FolkAttendee` instance, given the validated data.
        """
        folkattendee_id = self._kwargs.get("data", {}).get("id")
        new_folk = Folk.objects.filter(
            pk=self._kwargs.get("data", {}).get("folk", {}).get("id")
        ).first()
        # new_attendee_id = validated_data.get('attendee', {})
        if new_folk:
            validated_data["folk"] = new_folk
        # print("hi 27 here is validated_data: ", validated_data)
        # if new_attendee_id:
        #     # attendee, attendee_created = Attendee.objects.update_or_create(
        #     #     id=new_attendee_data.get('id'),
        #     #     defaults=new_attendee_data,
        #     # )
        #     attendee = Attendee.objects.get(pk=new_attendee_id)
        #     validated_data['attendee'] = attendee
        # Todo: 20210517  create relationships among families such as siblings, etc
        obj, created = FolkAttendee.objects.update_or_create(
            id=folkattendee_id,
            defaults=validated_data,
        )
        return obj

    def update(self, instance, validated_data):
        """
        Update and return an existing `FolkAttendee` instance, given the validated data.

        """
        new_folk = Folk.objects.filter(
            pk=self._kwargs.get("data", {}).get("folk", {}).get("id")
        ).first()
        # new_attendee_id = validated_data.get('attendee', {})
        # print("hi 49 here is validated_data: ", validated_data)
        if new_folk:
            # instance.folk = new_folk
            validated_data["folk"] = new_folk
        # else:
        #     validated_data['folk'] = instance.folk

        # if new_attendee_id:
        #     # attendee, attendee_created = Attendee.objects.update_or_create(
        #     #     id=instance.attendee.id,
        #     #     defaults=new_attendee_data,
        #     # )
        #     attendee = Attendee.objects.get(pk=new_attendee_id)
        #     validated_data['attendee'] = attendee
        # else:
        #     validated_data['attendee'] = instance.attendee
        # Todo: 20210517  update relationships among families such as siblings, etc
        obj, created = FolkAttendee.objects.update_or_create(
            id=instance.id,
            defaults=validated_data,
        )

        return obj
