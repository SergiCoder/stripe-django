"""Read-only reference-data endpoints for user profile dropdowns."""

from __future__ import annotations

from typing import ClassVar
from zoneinfo import available_timezones

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from saasmint_core.services.currency import SUPPORTED_CURRENCIES
from saasmint_core.services.locale import SUPPORTED_LOCALES


class LocaleListView(APIView):
    """GET /api/v1/locales/ — list supported locales."""

    permission_classes: ClassVar[list[type[AllowAny]]] = [AllowAny]  # type: ignore[misc]
    throttle_classes: ClassVar[list[type[ScopedRateThrottle]]] = [ScopedRateThrottle]  # type: ignore[misc]
    throttle_scope = "references"

    @extend_schema(responses={200: list[str]}, tags=["references"])
    def get(self, request: Request) -> Response:
        return Response(sorted(SUPPORTED_LOCALES))


class CurrencyListView(APIView):
    """GET /api/v1/currencies/ — list supported currencies."""

    permission_classes: ClassVar[list[type[AllowAny]]] = [AllowAny]  # type: ignore[misc]
    throttle_classes: ClassVar[list[type[ScopedRateThrottle]]] = [ScopedRateThrottle]  # type: ignore[misc]
    throttle_scope = "references"

    @extend_schema(responses={200: list[str]}, tags=["references"])
    def get(self, request: Request) -> Response:
        return Response(sorted(SUPPORTED_CURRENCIES))


_TIMEZONES: list[str] = sorted(available_timezones())


class TimezoneListView(APIView):
    """GET /api/v1/timezones/ — list IANA timezones."""

    permission_classes: ClassVar[list[type[AllowAny]]] = [AllowAny]  # type: ignore[misc]
    throttle_classes: ClassVar[list[type[ScopedRateThrottle]]] = [ScopedRateThrottle]  # type: ignore[misc]
    throttle_scope = "references"

    @extend_schema(responses={200: list[str]}, tags=["references"])
    def get(self, request: Request) -> Response:
        return Response(_TIMEZONES)
