from rest_framework import serializers
from schedule.models import Occurrence

from attendees.persons.models import Utility


class OccurrenceSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField(read_only=True)

    def get_text(self, obj):
        return f"{Utility.get_object_name(obj, 'title', 'meet_display_name') or ''} {Utility.get_object_name(obj, 'description', 'display_name') or ''}".strip() or obj.title or obj.description

    class Meta:
        model = Occurrence
        fields = '__all__'
