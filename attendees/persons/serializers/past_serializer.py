from rest_framework import serializers

from attendees.persons.models import Past


class PastSerializer(serializers.ModelSerializer):
    class Meta:  # It is critical not to have organization in the fields, to let perform_create set it
        model = Past
        fields = (
            "id",
            "display_name",
            "category",
            "when",
            "finish",
            "infos",
            "content_type",
            "object_id",
        )
