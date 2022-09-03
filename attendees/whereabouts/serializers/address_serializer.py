from address.models import Address
from rest_framework import serializers


class AddressSerializer(serializers.ModelSerializer):
    postal_code = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    state_id = serializers.SerializerMethodField(read_only=True)
    display_name = serializers.SerializerMethodField(read_only=True)

    def get_postal_code(self, obj):
        locality = obj.locality
        return locality.postal_code if locality else None

    def get_city(self, obj):
        locality = obj.locality
        return locality.name if locality else None

    def get_state_id(self, obj):
        locality = obj.locality
        return locality.state.id if locality else None

    def get_display_name(self, obj):
        return f'{obj.name}: {str(obj)}' if obj.name else str(obj)  # for gatherings_list_view page

    class Meta:
        model = Address
        fields = "__all__"

    #
    #
    #
    #
    #
    #
    # def create(self, validated_data):
    #     """
    #     Create or update `Address` instance, given the validated data.
    #     """
    #
    #     address_data = self._kwargs.get('data', {})
    #     address_id = address_data.get('id')
    #     locality_data = address_data.get('locality')
    #     print("hi 41 here is address_id:")
    #     print(address_id)
    #     print("hi 43 here is address_data:")
    #     print(address_data)
    #     print("hi 45 here is locality_data by address_data.get('locality'):")
    #     print(locality_data)
    #     print("hi 47 here is validated_data:")
    #     print(validated_data)
    #     print("hi 49 here is validated_data.get('locality', {}):")
    #     print(validated_data.get('locality', {}))
    #     obj, created = Address.objects.update_or_create(
    #         id=address_id,
    #         defaults=validated_data,
    #     )
    #     return obj
    #
    # def update(self, instance, validated_data):
    #     """
    #     Update and return an existing `Address` instance, given the validated data.
    #
    #     """
    #     # instance.title = validated_data.get('title', instance.title)
    #     # instance.code = validated_data.get('code', instance.code)
    #     # instance.linenos = validated_data.get('linenos', instance.linenos)
    #     # instance.language = validated_data.get('language', instance.language)
    #     # instance.style = validated_data.get('style', instance.style)
    #     instance.save()
    #     return instance
