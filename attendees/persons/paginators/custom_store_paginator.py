from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomStorePagination(LimitOffsetPagination):
    """
    default in setting's REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS
    """

    offset_query_param = "skip"
    limit_query_param = "take"

    def get_paginated_response(self, data):
        return Response(
            {
                "totalCount": self.count,
                "data": data,
            }
        )
