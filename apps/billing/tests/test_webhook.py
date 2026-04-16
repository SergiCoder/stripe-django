"""Tests for the Stripe webhook endpoint (sync-verify, sync-persist, 202 Accepted)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from apps.billing.models import StripeEvent
from apps.billing.webhook import stripe_webhook


@pytest.fixture
def rf():
    return RequestFactory()


def _make_event_payload(
    *,
    stripe_id: str = "evt_test_123",
    event_type: str = "checkout.session.completed",
    livemode: bool = False,
) -> str:
    return json.dumps(
        {
            "id": stripe_id,
            "type": event_type,
            "livemode": livemode,
            "data": {"object": {"id": "obj_123"}},
        }
    )


@pytest.fixture
def valid_payload() -> str:
    return _make_event_payload()


@pytest.mark.django_db
class TestStripeWebhook:
    @patch("apps.billing.webhook.process_stripe_webhook")
    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_valid_event_persists_and_enqueues_with_event_id(
        self, mock_construct, mock_task, rf, valid_payload, settings
    ):
        settings.STRIPE_SECRET_KEY = "sk_test_abc"
        mock_construct.return_value = MagicMock()
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=valid_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 202
        row = StripeEvent.objects.get(stripe_id="evt_test_123")
        assert row.type == "checkout.session.completed"
        assert row.livemode is False
        assert row.payload["data"]["object"]["id"] == "obj_123"
        mock_task.delay.assert_called_once_with(str(row.id))

    @patch("apps.billing.webhook.process_stripe_webhook")
    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_duplicate_event_is_not_re_enqueued(
        self, mock_construct, mock_task, rf, valid_payload, settings
    ):
        settings.STRIPE_SECRET_KEY = "sk_test_abc"
        mock_construct.return_value = MagicMock()
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=valid_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        first = stripe_webhook(request)
        second = stripe_webhook(
            rf.post(
                "/api/v1/webhooks/stripe/",
                data=valid_payload,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_test",
            )
        )

        assert first.status_code == 202
        assert second.status_code == 202
        assert StripeEvent.objects.filter(stripe_id="evt_test_123").count() == 1
        mock_task.delay.assert_called_once()

    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, mock_construct, rf, valid_payload):
        import stripe

        mock_construct.side_effect = stripe.SignatureVerificationError("bad sig", "sig")  # type: ignore[no-untyped-call]
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=valid_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 400
        assert not StripeEvent.objects.filter(stripe_id="evt_test_123").exists()

    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_invalid_json_returns_400(self, mock_construct, rf):
        mock_construct.side_effect = ValueError("Invalid JSON")
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data="not json",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 400

    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_missing_required_fields_returns_400(self, mock_construct, rf):
        """Payload that passes signature verification but lacks id/type/livemode
        is rejected with 400 — we can't persist a StripeEvent without them."""
        mock_construct.return_value = MagicMock()
        bad_payload = json.dumps({"type": "something", "livemode": False})
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=bad_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 400

    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_missing_signature_header_is_rejected_with_400(self, mock_construct, rf, valid_payload):
        """Stripe rejects an empty signature; we should surface 400 and never
        persist or enqueue. (Replaces a prior test that mocked the verifier
        into returning success on an empty signature.)"""
        import stripe

        mock_construct.side_effect = stripe.SignatureVerificationError("missing sig", "")  # type: ignore[no-untyped-call]
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=valid_payload,
            content_type="application/json",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 400
        assert not StripeEvent.objects.filter(stripe_id="evt_test_123").exists()

    @patch("apps.billing.webhook.process_stripe_webhook")
    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_livemode_mismatch_is_dropped_without_persisting(
        self, mock_construct, mock_task, rf, settings
    ):
        """Live event received against a test key (or vice versa) is dropped
        silently — 202, no StripeEvent row, no task enqueued."""
        settings.STRIPE_SECRET_KEY = "sk_test_abc"
        mock_construct.return_value = MagicMock()
        live_payload = _make_event_payload(stripe_id="evt_live_mismatch", livemode=True)
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=live_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 202
        assert not StripeEvent.objects.filter(stripe_id="evt_live_mismatch").exists()
        mock_task.delay.assert_not_called()

    @patch("apps.billing.webhook.process_stripe_webhook")
    @patch("apps.billing.webhook.stripe.Webhook.construct_event")
    def test_live_event_accepted_against_live_key(self, mock_construct, mock_task, rf, settings):
        settings.STRIPE_SECRET_KEY = "sk_live_abc"
        mock_construct.return_value = MagicMock()
        live_payload = _make_event_payload(stripe_id="evt_live_ok", livemode=True)
        request = rf.post(
            "/api/v1/webhooks/stripe/",
            data=live_payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test",
        )

        resp = stripe_webhook(request)

        assert resp.status_code == 202
        assert StripeEvent.objects.filter(stripe_id="evt_live_ok").exists()
        mock_task.delay.assert_called_once()
