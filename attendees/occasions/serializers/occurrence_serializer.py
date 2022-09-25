from rest_framework import serializers
from schedule.models import Occurrence


class OccurrenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Occurrence
        fields = '__all__'
