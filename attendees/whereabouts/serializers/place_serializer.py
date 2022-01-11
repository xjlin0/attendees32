from address.models import Address, Locality, State
from rest_framework import serializers

from attendees.whereabouts.models import Place
from attendees.whereabouts.serializers import AddressSerializer


class PlaceSerializer(serializers.ModelSerializer):
    """
    Generic relation: https://www.django-rest-framework.org/api-guide/relations/#generic-relationships
    """

    street = serializers.CharField(read_only=True)
    address = AddressSerializer(required=False)

    class Meta:
        model = Place
        # fields = '__all__'
        fields = [
            f.name for f in model._meta.fields if f.name not in ["is_removed"]
        ] + [
            "street",
            "address",
        ]

    def create(self, validated_data):
        """
        Create or update `Place` instance, given the validated data.
        """
        place_data = self._kwargs.get("data", {})
        place_id = place_data.get("id")
        address_data = place_data.get("address")
        address_id = address_data.get("id")
        locality = validated_data.get("address", {}).get("locality")

        print("hi 34 in PlaceSerializer here is validated_data:")
        print(validated_data)
        print("hi 36 in PlaceSerializer here is self._kwargs:")
        print(self._kwargs)

        if address_id and locality:
            new_city = address_data.get("city")
            new_zip = address_data.get("postal_code")
            new_state = State.objects.filter(pk=address_data.get("state_id")).first()

            if new_state:
                locality, locality_created = Locality.objects.update_or_create(
                    name=new_city,
                    postal_code=new_zip,
                    state=new_state,
                    defaults={
                        "name": new_city,
                        "postal_code": new_zip,
                        "state": new_state,
                    },
                )

            address_data["locality"] = locality
            address, address_created = Address.objects.update_or_create(
                id=address_id,
                defaults=address_data,
            )
            validated_data["address"] = address

            place, place_created = Place.objects.update_or_create(
                id=place_id,
                defaults=validated_data,
            )
        else:  # user is creating new address, new_address is to bypass DRF model validations
            new_address_data = address_data.get("new_address", {})
            del validated_data["address"]

            place, place_created = Place.objects.update_or_create(
                id=place_id,
                defaults=validated_data,
            )
            place.address = new_address_data
            place.save()

        return place

    def update(self, instance, validated_data):
        """
        Update and return an existing `Place` instance, given the validated data.

        """
        print("hi 84 in PlaceSerializer here is instance:")
        print(instance)
        print("hi 86 in PlaceSerializer here is validated_data:")
        print(validated_data)
        print("hi 88 in PlaceSerializer here is self._kwargs:")
        print(self._kwargs)

        place_data = self._kwargs.get("data", {})
        # place_id = instance.id
        address_data = place_data.get("address")
        address_id = address_data.get("id")
        locality = validated_data.get("address", {}).get("locality")

        if address_id and locality:
            new_city = address_data.get("city")
            new_zip = address_data.get("postal_code")
            new_state = State.objects.filter(pk=address_data.get("state_id")).first()
            print("hi 101 in PlaceSerializer processing state/locality")
            if new_state:
                locality, locality_created = Locality.objects.update_or_create(
                    name=new_city,
                    postal_code=new_zip,
                    state=new_state,
                    defaults={
                        "name": new_city,
                        "postal_code": new_zip,
                        "state": new_state,
                    },
                )

            address_data["locality"] = locality
            address, address_created = Address.objects.update_or_create(
                id=address_id,
                defaults=address_data,
            )
            validated_data["address"] = address

            place, place_created = Place.objects.update_or_create(
                id=instance.id,
                defaults=validated_data,
            )
        else:  # user is creating new address, new_address is to bypass DRF model validations
            new_address_data = address_data.get("new_address", {})
            del validated_data["address"]
            print("hi 128 in PlaceSerializer here is address_data:")
            print(address_data)
            print("hi 130 in PlaceSerializer here is after removal validated_data:")
            print(validated_data)
            place, place_created = Place.objects.update_or_create(
                id=instance.id,
                defaults=validated_data,
            )
            place.address = new_address_data
            place.save()

        return place
