# from .attendee import AttendeeSerializer
from rest_framework import serializers

from attendees.persons.models import Attending
from attendees.persons.serializers import AttendeeMinimalSerializer


class AttendingAttendeeSerializer(serializers.ModelSerializer):
    # meets_info = serializers.SerializerMethodField()
    attendee = AttendeeMinimalSerializer(many=False, read_only=True)

    # def get_meets_info(self, obj):
    #     return {am.meet.slug: am.character.display_name for am in obj.attendingmeet_set.all()}

    class Meta:
        model = Attending
        fields = "__all__"
        # fields = [f.name for f in model._meta.fields if f.name not in ['is_removed']]  # + [
        #     'attending_label',
        #     'meets_info',
        #     'attendee',
        # ]
