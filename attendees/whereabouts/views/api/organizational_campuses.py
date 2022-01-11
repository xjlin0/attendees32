import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.viewsets import ModelViewSet

from attendees.whereabouts.models import Campus
from attendees.whereabouts.serializers import CampusSerializer


class ApiOrganizationalCampusViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Campus to be viewed or edited.
    """

    serializer_class = CampusSerializer

    def get_queryset(self, **kwargs):
        """attendees/occasions/views/api/organization_meets.pyattendees/occasions/views/api/organization_meets.py
        Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help,
              check if args[i] = JSON.stringify(loadOptions[i]) help
        :param kwargs:
        :return:
        """
        if self.request.user.organization:
            campus_id = self.request.query_params.get("id", None)
            keywords = (self.request.query_params.get("searchValue", ""),)
            keyword = "".join(
                map(str, keywords)
            )

            if campus_id:
                return Campus.objects.filter(
                    pk=campus_id,
                    organization=self.request.user.organization,
                )
            else:
                return Campus.objects.filter(
                    display_name__icontains=keyword,
                    organization=self.request.user.organization,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


api_organizational_campus_view_set = ApiOrganizationalCampusViewSet
