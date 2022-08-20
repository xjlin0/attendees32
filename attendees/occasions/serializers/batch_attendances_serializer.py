from rest_framework import serializers
#
# from attendees.occasions.services import AttendanceService
# from attendees.persons.models.utility import AttendanceBatchCreateResult


class BatchAttendancesSerializer(serializers.Serializer):
    number_created = serializers.IntegerField(read_only=True)
    begin = serializers.DateTimeField()
    end = serializers.DateTimeField()
    meet_slug = serializers.CharField()
    # duration = serializers.IntegerField(required=False)
    # schedule_rules = serializers.JSONField(read_only=True)

    # class Meta:
    #     model = AttendanceBatchCreateResult
    #     fields = ['begin', 'end', 'meet']

    def create(self, validated_data):
        """
        Create `Attendance` instances based on datetime ranges, won't repeat create if already exist

        """
        pass
