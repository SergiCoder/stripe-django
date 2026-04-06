"""Tests for services/supabase_admin.py — user and avatar deletion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from saasmint_core.services.supabase_admin import (
    _extract_storage_path,
    delete_supabase_avatar,
    delete_supabase_user,
)

_SUPABASE_URL = "http://localhost:54321"
_SERVICE_ROLE_KEY = "test-service-role-key"


def _mock_httpx_client(status_code: int = 200, text: str = "") -> AsyncMock:
    """Build a mock httpx.AsyncClient that returns the given status."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = text
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.delete = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client, mock_resp


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


def test_extract_storage_path_bucket_only_no_subpath() -> None:
    """A URL with just a bucket name and no sub-path returns bucket only."""
    url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars"
    result = _extract_storage_path(url, _SUPABASE_URL)
    assert result == "avatars"


# ── delete_supabase_user ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_delete_user_empty_service_key_skips() -> None:
    """When service_role_key is empty, deletion is skipped."""
    with patch("saasmint_core.services.supabase_admin.httpx.AsyncClient") as mock_cls:
        await delete_supabase_user(
            supabase_url=_SUPABASE_URL,
            service_role_key="",
            supabase_uid="uid_123",
        )
    mock_cls.assert_not_called()


@pytest.mark.anyio
async def test_delete_user_success_200() -> None:
    mock_client, _mock_resp = _mock_httpx_client(status_code=200)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await delete_supabase_user(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            supabase_uid="uid_200",
        )

    mock_client.delete.assert_called_once_with(
        f"{_SUPABASE_URL}/auth/v1/admin/users/uid_200",
        headers={
            "apikey": _SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {_SERVICE_ROLE_KEY}",
        },
    )


@pytest.mark.anyio
async def test_delete_user_success_204() -> None:
    mock_client, _ = _mock_httpx_client(status_code=204)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await delete_supabase_user(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            supabase_uid="uid_204",
        )

    mock_client.delete.assert_called_once()


@pytest.mark.anyio
async def test_delete_user_404_already_deleted() -> None:
    """404 is treated as success (user already deleted)."""
    mock_client, _ = _mock_httpx_client(status_code=404)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        # Should not raise
        await delete_supabase_user(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            supabase_uid="uid_gone",
        )


@pytest.mark.anyio
async def test_delete_user_error_raises() -> None:
    """Non-success, non-404 status codes raise via raise_for_status."""
    import httpx

    mock_client, mock_resp = _mock_httpx_client(status_code=500, text="Internal error")
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_resp)
    )

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        with pytest.raises(httpx.HTTPStatusError):
            await delete_supabase_user(
                supabase_url=_SUPABASE_URL,
                service_role_key=_SERVICE_ROLE_KEY,
                supabase_uid="uid_500",
            )


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
async def test_delete_avatar_empty_service_key_is_noop() -> None:
    with patch("saasmint_core.services.supabase_admin.httpx.AsyncClient") as mock_cls:
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key="",
            avatar_url=f"{_SUPABASE_URL}/storage/v1/object/public/avatars/user/photo.png",
        )
    mock_cls.assert_not_called()


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
    mock_client, _ = _mock_httpx_client(status_code=200)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=avatar_url,
        )

    mock_client.delete.assert_called_once_with(
        f"{_SUPABASE_URL}/storage/v1/object/avatars/user123/photo.png",
        headers={
            "apikey": _SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {_SERVICE_ROLE_KEY}",
        },
    )


@pytest.mark.anyio
async def test_delete_avatar_404_already_deleted() -> None:
    """404 is silently accepted (avatar already gone)."""
    avatar_url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars/user123/photo.png"
    mock_client, _ = _mock_httpx_client(status_code=404)

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=avatar_url,
        )

    mock_client.delete.assert_called_once()


@pytest.mark.anyio
async def test_delete_avatar_error_status_logged_not_raised() -> None:
    """Non-success, non-404 status is logged but does not raise."""
    avatar_url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars/user123/photo.png"
    mock_client, _ = _mock_httpx_client(status_code=500, text="Internal error")

    with patch(
        "saasmint_core.services.supabase_admin.httpx.AsyncClient",
        return_value=mock_client,
    ):
        # Should not raise — avatar errors are non-fatal
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=avatar_url,
        )


@pytest.mark.anyio
async def test_delete_avatar_bucket_only_path_skipped() -> None:
    """When the URL has a bucket but no sub-path, deletion is skipped."""
    avatar_url = f"{_SUPABASE_URL}/storage/v1/object/public/avatars"
    with patch("saasmint_core.services.supabase_admin.httpx.AsyncClient") as mock_cls:
        await delete_supabase_avatar(
            supabase_url=_SUPABASE_URL,
            service_role_key=_SERVICE_ROLE_KEY,
            avatar_url=avatar_url,
        )
    mock_cls.assert_not_called()
