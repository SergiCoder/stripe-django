"""Tests for OpenAPI schema and documentation endpoints (Swagger, ReDoc)."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
class TestOpenAPIEndpoints:
    def test_schema_endpoint_returns_json(self):
        client = Client()
        resp = client.get("/api/schema/")
        assert resp.status_code == 200

    def test_swagger_ui_returns_html(self):
        client = Client()
        resp = client.get("/api/docs/")
        assert resp.status_code == 200
        assert b"swagger" in resp.content.lower() or b"openapi" in resp.content.lower()

    def test_redoc_returns_html(self):
        client = Client()
        resp = client.get("/api/redoc/")
        assert resp.status_code == 200

    def test_schema_excludes_admin_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/admin/" not in content

    def test_schema_excludes_webhook_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/api/v1/webhooks/" not in content

    def test_schema_excludes_dashboard_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/dashboard/" not in content

    def test_schema_excludes_hijack_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/hijack/" not in content

    def test_schema_includes_billing_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/api/v1/billing/" in content

    def test_schema_includes_account_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/api/v1/account/" in content

    def test_schema_includes_orgs_paths(self):
        client = Client()
        resp = client.get("/api/schema/", HTTP_ACCEPT="application/json")
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "/api/v1/orgs/" in content
