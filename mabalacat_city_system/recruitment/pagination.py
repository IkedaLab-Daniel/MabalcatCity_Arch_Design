"""Pagination classes for recruitment API endpoints."""

from rest_framework.pagination import PageNumberPagination


class RecruitmentPagination(PageNumberPagination):
    """Default page-number pagination for recruitment resources."""

    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"
