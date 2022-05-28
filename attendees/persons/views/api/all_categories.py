from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets

from attendees.persons.models import Category
from attendees.persons.serializers import CategorySerializer


class ApiAllCategoriesViewsSet(LoginRequiredMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Category to be viewed or edited.
    """

    serializer_class = CategorySerializer

    def get_queryset(self):
        categories_id = self.kwargs.get("pk")
        type = self.request.query_params.get("type")
        search_value = self.request.query_params.get("searchValue")
        search_operation = self.request.query_params.get("searchOperation")

        extra_filters = {}

        if categories_id:
            extra_filters['pk'] = categories_id
        if type:
            extra_filters['type'] = type
        if search_value and search_operation == 'contains':
            extra_filters['display_name__icontains'] = search_value

        return Category.objects.filter(**extra_filters).order_by("display_order")


api_all_categories_viewset = ApiAllCategoriesViewsSet
