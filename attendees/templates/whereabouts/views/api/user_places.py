import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import AuthenticationFailed
from attendees.whereabouts.models import Place
from attendees.whereabouts.serializers import PlaceMinimalSerializer


class ApiUserPlaceViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Place to be viewed or edited.
    """
    serializer_class = PlaceMinimalSerializer

    def get_queryset(self, **kwargs):
        if self.request.user.organization:
            # Todo: 20210502 filter contacts the current user can see (for schedulers)
            place_id = self.request.query_params.get('id', None)
            keywords = self.request.query_params.get('searchValue', ''),
            keyword = ''.join(map(str, keywords))  # Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help, check if args[i] = JSON.stringify(loadOptions[i]) help
            places = Place.objects if self.request.user.privileged() else self.request.user.attendee.contacts

            if place_id:
                return places.filter(
                    pk=place_id,
                    organization=self.request.user.organization,
                )
            else:
                return places.filter(
                    (Q(address__street_number__icontains=keyword)
                     |
                     Q(display_name__icontains=keyword)
                     |
                     Q(address__route__icontains=keyword)
                     |
                     Q(address__raw__icontains=keyword)),
                    organization=self.request.user.organization,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(detail='Have your account assigned an organization?')


api_user_place_view_set = ApiUserPlaceViewSet
