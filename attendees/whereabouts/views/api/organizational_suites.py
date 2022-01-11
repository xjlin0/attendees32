import time

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.viewsets import ModelViewSet

from attendees.whereabouts.models import Suite
from attendees.whereabouts.serializers import SuiteSerializer


class ApiOrganizationalSuiteViewSet(LoginRequiredMixin, ModelViewSet):
    """
    API endpoint that allows Suite to be viewed or edited.
    """

    serializer_class = SuiteSerializer

    def get_queryset(self, **kwargs):
        """
        Todo: crazy params parsed as tuple, add JSON.stringify() on ajax does not help,
              check if args[i] = JSON.stringify(loadOptions[i]) help
        :param kwargs:
        :return:
        """
        if self.request.user.organization:
            suite_id = self.request.query_params.get("id", None)
            keywords = (self.request.query_params.get("searchValue", ""),)
            keyword = "".join(
                map(str, keywords)
            )
            print("hi 23 here is self.request.query_params: ")
            print(self.request.query_params)
            if suite_id:
                return Suite.objects.filter(
                    pk=suite_id,
                    property__campus__organization=self.request.user.organization,
                )
            else:
                return Suite.objects.filter(
                    display_name__icontains=keyword,
                    property__campus__organization=self.request.user.organization,
                )

        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


api_organizational_suite_view_set = ApiOrganizationalSuiteViewSet
