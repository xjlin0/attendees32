import time

from address.models import State
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import AuthenticationFailed

from attendees.whereabouts.serializers import StateSerializer


class ApiAllStateViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Place to be viewed or edited.
    """
    serializer_class = StateSerializer

    def get_queryset(self, **kwargs):
        if self.request.user.organization:
            state_id = self.request.query_params.get('id', None)
            keywords = self.request.query_params.get('searchValue', ''),
            keyword = ''.join(map(str, keywords))  # Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help, check if args[i] = JSON.stringify(loadOptions[i]) help

            if state_id:
                return State.objects.filter(pk=state_id)
            else:
                return State.objects.filter(
                    Q(name__icontains=keyword)
                    |
                    Q(code__icontains=keyword)
                    |
                    Q(country__name__icontains=keyword)
                ).order_by(
                    'country__code',
                    'name',
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(detail='Have your account assigned an organization?')


api_all_state_view_set = ApiAllStateViewSet
