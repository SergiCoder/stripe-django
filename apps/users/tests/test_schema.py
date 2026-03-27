"""Tests for the drf-spectacular SupabaseJWT authentication extension."""

from __future__ import annotations

from apps.users.schema import SupabaseJWTAuthenticationScheme


class TestSupabaseJWTAuthenticationScheme:
    def test_target_class_is_correct(self):
        assert (
            SupabaseJWTAuthenticationScheme.target_class
            == "apps.users.authentication.SupabaseJWTAuthentication"
        )

    def test_name_is_supabase_jwt(self):
        assert SupabaseJWTAuthenticationScheme.name == "SupabaseJWT"

    def test_get_security_definition_returns_bearer_scheme(self):
        extension = SupabaseJWTAuthenticationScheme(target=None)
        defn = extension.get_security_definition(auto_schema=None)
        assert defn["type"] == "http"
        assert defn["scheme"] == "bearer"
        assert defn["bearerFormat"] == "JWT"

    def test_get_security_definition_includes_description(self):
        extension = SupabaseJWTAuthenticationScheme(target=None)
        defn = extension.get_security_definition(auto_schema=None)
        assert "description" in defn
        assert "Supabase" in defn["description"]
