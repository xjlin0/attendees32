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
        if categories_id:
            return Category.objects.filter(pk=categories_id)
        else:
            return Category.objects.filter(type=type).order_by("display_order")


api_all_categories_viewset = ApiAllCategoriesViewsSet
