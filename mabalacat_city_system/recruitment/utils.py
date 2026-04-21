"""Utility helpers for API response consistency."""

from rest_framework import status
from rest_framework.response import Response


def error_response(detail: str, code: str, field_errors: dict | None = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """Return a standardized error payload for recruitment endpoints."""

    return Response(
        {
            "detail": detail,
            "code": code,
            "field_errors": field_errors or {},
        },
        status=status_code,
    )
