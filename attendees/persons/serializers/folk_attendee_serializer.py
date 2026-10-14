from rest_framework import serializers

from attendees.persons.models import Folk, FolkAttendee
from attendees.persons.serializers import FolkSerializer


class FolkField(serializers.PrimaryKeyRelatedField):
    """
    Written as a folk id, read back as the nested folk.

    Every writer (the attendee page's family grid, API clients) names the folk
    by id, while readers take folk.display_name and folk.category straight off
    each row, so the field is a plain primary key on the way in and the
    FolkSerializer's output on the way out.
    """

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return FolkSerializer(value, context=self.context).data


class FolkAttendeeSerializer(serializers.ModelSerializer):
    folk = FolkField(queryset=Folk.objects.all())
    file_path = serializers.SerializerMethodField(required=False, read_only=True)

    class Meta:
        model = FolkAttendee
        fields = "__all__"

    def get_file_path(self, obj):
        return obj.file.url if obj.file else ""
