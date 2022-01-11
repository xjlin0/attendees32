import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import AuthenticationFailed

from attendees.whereabouts.models import Room
from attendees.whereabouts.serializers import RoomSerializer


class ApiOrganizationalRoomViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Suite to be viewed or edited.
    """
    serializer_class = RoomSerializer

    def get_queryset(self, **kwargs):
        if self.request.user.organization:
            room_id = self.request.query_params.get('id', None)
            keywords = self.request.query_params.get('searchValue', ''),
            keyword = ''.join(map(str, keywords))  # Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help, check if args[i] = JSON.stringify(loadOptions[i]) help
            print("hi 22 here is self.request.query_params: "); print(self.request.query_params)
            if room_id:
                return Room.objects.filter(
                    pk=room_id,
                    suite__property__campus__organization=self.request.user.organization,
                )
            else:
                return Room.objects.filter(
                    display_name__icontains=keyword,
                    suite__property__campus__organization=self.request.user.organization,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(detail='Have your account assigned an organization?')


api_organizational_room_view_set = ApiOrganizationalRoomViewSet
