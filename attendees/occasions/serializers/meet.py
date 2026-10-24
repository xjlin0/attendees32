from rest_framework import serializers

from attendees.occasions.models import Meet


class MeetSerializer(serializers.ModelSerializer):
    assembly_name = serializers.CharField(required=False)
    schedule_rules = serializers.JSONField(read_only=True)
    show_attendee_infos = serializers.SerializerMethodField(read_only=True)
    division = serializers.IntegerField(source="assembly.division_id", read_only=True)

    class Meta:
        model = Meet
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "assembly_name",
            "schedule_rules",
            "show_attendee_infos",
            "division",
        ]

    def get_show_attendee_infos(self, obj):
        if obj.assembly and obj.assembly.division and obj.assembly.division.infos:
            return obj.assembly.division.infos.get("show_attendee_infos", {})
        return {}
