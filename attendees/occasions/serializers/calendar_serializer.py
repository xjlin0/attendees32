from rest_framework import serializers
from schedule.models import Calendar


class CalendarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Calendar
        fields = '__all__'
