"""Request/response serializers for the users app."""

from __future__ import annotations

from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "avatar_url",
            "account_type",
            "preferred_locale",
            "preferred_currency",
            "phone",
            "timezone",
            "job_title",
            "bio",
            "is_verified",
            "created_at",
        )
        read_only_fields = fields


class UpdateUserSerializer(serializers.Serializer[User]):
    full_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    avatar_url = serializers.URLField(required=False, allow_null=True)
    preferred_locale = serializers.CharField(max_length=10, required=False)
    preferred_currency = serializers.CharField(max_length=3, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_null=True)
    timezone = serializers.CharField(max_length=50, required=False, allow_null=True)
    job_title = serializers.CharField(max_length=100, required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_null=True)

    def validate_preferred_locale(self, value: str) -> str:
        from saasmint_core.services.locale import SUPPORTED_LOCALES

        return self._validate_in_set(value, SUPPORTED_LOCALES, "locale")

    def validate_preferred_currency(self, value: str) -> str:
        from saasmint_core.services.currency import SUPPORTED_CURRENCIES

        return self._validate_in_set(value, SUPPORTED_CURRENCIES, "currency")

    @staticmethod
    def _validate_in_set(value: str, allowed: frozenset[str], label: str) -> str:
        if value not in allowed:
            raise serializers.ValidationError(
                f"Unsupported {label}. Must be one of: {', '.join(sorted(allowed))}"
            )
        return value
