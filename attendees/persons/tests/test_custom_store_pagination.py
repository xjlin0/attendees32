import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from attendees.persons.paginators.custom_store_paginator import CustomStorePagination

class TestCustomStorePagination:
    def setup_method(self):
        self.pagination = CustomStorePagination()
        self.factory = APIRequestFactory()

    def test_pagination_parameters(self):
        assert self.pagination.offset_query_param == "skip"
        assert self.pagination.limit_query_param == "take"

    def test_get_paginated_response(self):
        data = [{"id": 1, "name": "Test"}]
        self.pagination.count = 100
        
        response = self.pagination.get_paginated_response(data)
        
        assert response.status_code == 200
        assert response.data == {
            "totalCount": 100,
            "data": data,
        }

    def test_paginate_queryset(self):
        queryset = list(range(100))
        factory_request = self.factory.get('/', {'skip': 10, 'take': 5})
        request = Request(factory_request)
        
        paginated_data = self.pagination.paginate_queryset(queryset, request)
        
        assert paginated_data == [10, 11, 12, 13, 14]
        assert self.pagination.count == 100
        assert self.pagination.offset == 10
        assert self.pagination.limit == 5
