"""Tests for services/supabase_admin.py — avatar deletion."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from saasmint_core.services.supabase_admin import _extract_storage_path, delete_supabase_avatar

_SUPABASE_URL = "http://localhost:54321"
_SERVICE_ROLE_KEY = "test-service-role-key"


# ── _extract_storage_path ───────────────────────────────────────────────────


def test_extract_storage_path_valid_url() -> None:
    url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars/user123/photo.png"
    assert _extract_storage_path(url, _SUPABASE_URL) == "avatars/user123/photo.png"


def test_extract_storage_path_external_url() -> None:
    url = "https://cdn.example.com/images/photo.png"
    assert _extract_storage_path(url, _SUPABASE_URL) is None


def test_extract_storage_path_wrong_path_prefix() -> None:
    url = f"{_SUPABASE_URL}/auth/v1/something"
    assert _extract_storage_path(url, _SUPABASE_URL) is None


# ── delete_supabase_avatar ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_avatar_none_is_noop() -> None:
    with patch("saasmint_core.services.supabase_admin.httpx.AsyncClient") as mock_client:
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=None,
        )
    mock_client.assert_not_called()


@pytest.mark.anyio
async def test_delete_avatar_external_url_skipped() -> None:
    with patch("saasmint_core.services.supabase_admin.httpx.AsyncClient") as mock_client:
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url="https://cdn.example.com/photo.png",
        )
    mock_client.assert_not_called()


@pytest.mark.anyio
async def test_delete_avatar_success() -> None:
    avatar_url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars/user123/photo.png"
    mock_resp = AsyncMock()
    mock_resp.status_code = 200

    mock_client_instance = AsyncMock()
    mock_client_instance.delete = AsyncMock(return_value=mock_resp)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client_instance,
    ):
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=avatar_url,
        )

    mock_client_instance.delete.assert_called_once_with(
        f"{_SUPABASE_URL}/storage/v1/object/avatars/user123/photo.png",
        headers={
            "apikey": _SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {_SERVICE_ROLE_KEY}",
        },
    )
