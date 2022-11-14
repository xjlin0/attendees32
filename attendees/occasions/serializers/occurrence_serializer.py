from rest_framework import serializers
from schedule.models import Occurrence

from attendees.persons.models import Utility


class OccurrenceSerializer(serializers.ModelSerializer):
    """
    Note: the "allDay:" string in the beginning of the description will be rendered as all day event
    """
    text = serializers.SerializerMethodField(read_only=True)
    color = serializers.SerializerMethodField(read_only=True)
    calendar = serializers.SerializerMethodField(read_only=True)

    def get_text(self, obj):
        if obj.id:
            event_name = Utility.get_object_name(obj, 'title', 'meet_display_name') or ''
        else:
            meet = obj.event.eventrelation_set.filter(distinction='source').first()
            location = obj.event.eventrelation_set.filter(distinction='location').first()
            if meet:
                event_name = str(meet.content_object)
            elif location:
                event_name = str(location.content_object)
            else:
                event_name = obj.event.title
        location_name = Utility.get_object_name(obj, 'description', 'display_name') or ''
        return f"{event_name.strip()} {location_name}".strip() or obj.title or obj.description

    def get_color(self, obj):
        color_code = obj.event and obj.event.color_event
        return color_code if color_code and color_code.startswith('#') else None

    def get_calendar(self, obj):
        return obj.event.calendar_id

    class Meta:
        model = Occurrence
        fields = '__all__'
