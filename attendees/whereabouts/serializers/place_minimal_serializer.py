from rest_framework import serializers

from attendees.whereabouts.models import Place


class PlaceMinimalSerializer(serializers.ModelSerializer):
    street = serializers.CharField(read_only=True)

    class Meta:
        model = Place
        fields = "__all__"
        # fields = [f.name for f in model._meta.fields if f.name not in ['is_removed']] + [
        #     'street',  # causing 'Object of type Address is not JSON serializable'
        # ]
        # use read_only_fields = ()
