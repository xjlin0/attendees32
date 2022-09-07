from rest_framework import serializers

from attendees.occasions.models import Attendance
from attendees.persons.models import Utility


class AttendanceEtcSerializer(serializers.ModelSerializer):
    gathering__meet__assembly = serializers.IntegerField(read_only=True, source='assembly')
    gathering__meet = serializers.IntegerField(read_only=True, source='meet')
    gathering__display_name = serializers.CharField(read_only=True, source='gathering_name')
    attendee_id = serializers.CharField(read_only=True)
    attending__attendee__infos__names__original = serializers.CharField(read_only=True, source='attending_name')
    photo = serializers.CharField(read_only=True)
    file = serializers.FileField(use_url=True, allow_empty_file=True, allow_null=True)  # cause 400
    encoded_file = serializers.CharField(required=False)

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
        print("hi 36 here is instance.__dict__: ", instance.__dict__)
        # if (
        #     True
        # ):  # need validations such as if the assembly matching meet, it's better to validate on UI first
            # instance.meet = validated_data.get("meet", instance.meet)
            # instance.meet.assembly = validated_data.get('assembly', instance.meet.assembly)
            # instance.meet.save()
        print("hi 43 here is validated_data: ", validated_data)
        instance.gathering = validated_data.get("gathering", instance.gathering)
        instance.attending = validated_data.get("attending", instance.attending)
        instance.start = validated_data.get("start", instance.start)
        instance.finish = validated_data.get("finish", instance.finish)
        instance.character = validated_data.get("character", instance.character)
        instance.category = validated_data.get("category", instance.category)
        instance.team = validated_data.get("team", instance.team)
        instance.infos = {**instance.infos, **validated_data.get("infos", {})}
        instance.file = validated_data.get("file", instance.file)
        encoded_file = validated_data.get('encoded_file')



        # if encoded_file:  # https://stackoverflow.com/a/34870506/4257237
        #     img_dict = re.match("data:(?P<type>.*?);(?P<encoding>.*?),(?P<data>.*)", encoded_file).groupdict()
        #     print("hi 61 here is img_dict: ", img_dict)
        #     blob = img_dict['data'].decode(img_dict['encoding'], 'strict')
        #     print("hi 63 here is blob: ", blob)
        #     with io.BytesIO(blob) as stream:
        #         signature_file = File(stream)
        #         instance.file.save("ttt.svg", signature_file)
        #  'data:image/svg+xml;base64,PHN2ZyB4bWxucz
        if encoded_file:  # 'data:image/svg+xml;base64,PHN2ZyB4bWxucz
            file_name = 'test001.svg'
            instance.file.save(file_name, Utility.base64_file(encoded_file, 'test001'), save=True)




        instance.save()
        return instance
