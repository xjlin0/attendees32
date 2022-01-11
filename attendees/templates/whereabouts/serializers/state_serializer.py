from address.models import State
from rest_framework import serializers


class StateSerializer(serializers.ModelSerializer):
    country_code = serializers.SerializerMethodField()
    country_name = serializers.SerializerMethodField()

    def get_country_code(self, obj):
        country = obj.country
        return country.code if country else None

    def get_country_name(self, obj):
        country = obj.country
        return country.name if country else None

    class Meta:
        model = State
        fields = '__all__'

