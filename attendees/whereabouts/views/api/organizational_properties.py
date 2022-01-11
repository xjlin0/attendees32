import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.viewsets import ModelViewSet

from attendees.whereabouts.models import Property
from attendees.whereabouts.serializers import PropertySerializer


class ApiOrganizationalPropertyViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Property to be viewed or edited.
    """

    serializer_class = PropertySerializer

    def get_queryset(self, **kwargs):
        """
        Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help,
              check if args[i] = JSON.stringify(loadOptions[i]) help
        :param kwargs:
        :return:
        """
        if self.request.user.organization:
            property_id = self.request.query_params.get("id", None)
            keywords = (self.request.query_params.get("searchValue", ""),)
            keyword = "".join(
                map(str, keywords)
            )

            if property_id:
                return Property.objects.filter(
                    pk=property_id,
                    campus__organization=self.request.user.organization,
                )
            else:
                return Property.objects.filter(
                    display_name__icontains=keyword,
                    campus__organization=self.request.user.organization,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


api_organizational_property_view_set = ApiOrganizationalPropertyViewSet
