from rest_framework import serializers

from attendees.persons.models import Utility


class MeetListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        meets = (
            data.all()
            if hasattr(data, "all")
            else (data if isinstance(data, (list, tuple)) else [])
        )
        events = [
            er.event
            for meet in meets
            for er in meet.event_relations.all()
            if getattr(er, "distinction", None) == "source" and getattr(er, "event", None)
        ]
        if events:
            Utility.batch_preload_object_names(events, method_name="description")

        return super().to_representation(data)
