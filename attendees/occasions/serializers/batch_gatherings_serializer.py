from rest_framework import serializers
#
# from attendees.occasions.services import GatheringService
# from attendees.persons.models.utility import GatheringBatchCreateResult


class BatchGatheringsSerializer(serializers.Serializer):
    number_created = serializers.IntegerField(read_only=True)
    begin = serializers.DateTimeField()
    end = serializers.DateTimeField()
    meet_slug = serializers.CharField()
    duration = serializers.IntegerField(required=False)
    # schedule_rules = serializers.JSONField(read_only=True)

    # class Meta:
    #     model = GatheringBatchCreateResult
    #     fields = ['begin', 'end', 'meet']

    def create(self, validated_data):
        """
        Create `Gathering` instances based on datetime ranges, won't repeat create if already exist

        """
        # print("hi 23 BatchGatheringsSerializer here is validated_data: ")
        # print(validated_data)
        # print("hi 24 BatchGatheringsSerializer here is self: ")
        # print(self)
        # result = GatheringService.batch_create(validated_data)
        # return GatheringBatchCreateResult(number_created=result, **validated_data)
        pass
