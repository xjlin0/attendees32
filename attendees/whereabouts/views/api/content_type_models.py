import time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView

from attendees.whereabouts.serializers import ContentTypeSerializer


class ApiContentTypeListAPIView(LoginRequiredMixin, ListAPIView):
    """
    Restricted endpoint that allows ContentType to be viewed, need search params of 'query' to filter the models.
    """

    serializer_class = ContentTypeSerializer
    model = ContentType

    def get_queryset(self):
        if self.request.user.organization:
            content_type_id = self.kwargs.get("pk")
            query = self.request.query_params.get("query")
            if content_type_id:
                return ContentType.objects.raw(
                    f"SELECT * FROM {ContentType.objects.model._meta.db_table} WHERE id = %s AND genres LIKE %s",
                    [content_type_id, query],
                )
            else:
                return ContentType.objects.raw(
                    f"SELECT * FROM {ContentType.objects.model._meta.db_table} WHERE genres LIKE %s ORDER BY display_order",
                    [query],
                )
        else:
            time.sleep(2)
            raise AuthenticationFailed(
                detail="Have your account assigned an organization?"
            )


content_type_list_api_view = ApiContentTypeListAPIView
