from rest_framework import serializers
from schedule.models import Occurrence

from attendees.persons.models import Utility


class OccurrenceSerializer(serializers.ModelSerializer):
    """
    Note: the "allDay:" string in the beginning of the description will be rendered as all day event
    """
    text = serializers.SerializerMethodField(read_only=True)

    def get_text(self, obj):
        if obj.id:
            event_name = Utility.get_object_name(obj, 'title', 'meet_display_name') or ''
        else:
            meet = obj.event.eventrelation_set.filter(distinction='source').first()
            if meet:
                event_name = str(meet.content_object)
            else:
                event_name = obj.event.title
        location_name = Utility.get_object_name(obj, 'description', 'display_name') or ''
        return f"{event_name.strip()} {location_name}".strip() or obj.title or obj.description

    class Meta:
        model = Occurrence
        fields = '__all__'
