import time

from address.models import Address
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import AuthenticationFailed

from attendees.whereabouts.serializers import AddressSerializer


class ApiAllAddressViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Place to be viewed or edited.
    """
    serializer_class = AddressSerializer

    def get_queryset(self, **kwargs):
        if self.request.user.organization:
            address_id = self.request.query_params.get('id', None)
            keywords = self.request.query_params.get('searchValue', ''),
            keyword = ''.join(map(str, keywords))  # Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help, check if args[i] = JSON.stringify(loadOptions[i]) help

            if address_id:
                return Address.objects.filter(pk=address_id)
            else:
                return Address.objects.filter(
                    Q(street_number__icontains=keyword)
                    |
                    Q(route__icontains=keyword)
                    |
                    Q(raw__icontains=keyword)
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(detail='Have your account assigned an organization?')


api_all_address_view_set = ApiAllAddressViewSet
