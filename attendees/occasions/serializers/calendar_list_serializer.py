from rest_framework import serializers
from schedule.models import Calendar


class CalendarListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Calendar
