"""Transactional billing emails using Resend."""

from __future__ import annotations

import logging

import resend
from django.conf import settings

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, html: str) -> None:
    if not resend.api_key:
        resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send(
        {
            "from": settings.EMAIL_FROM_ADDRESS,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )


def send_subscription_cancel_scheduled(email: str, subscription_label: str) -> None:
    """Notify that a subscription has been scheduled to cancel at period end."""
    _send(
        to=email,
        subject="Your subscription is scheduled to cancel",
        html=(
            f"<p>The subscription for <strong>{subscription_label}</strong> has been"
            " scheduled to cancel at the end of the current billing period.</p>"
            "<p>You can resume it before the period ends from your billing settings.</p>"
        ),
    )
    logger.info("Subscription cancel-scheduled email sent to %s", email)


def send_subscription_cancel_resumed(email: str, subscription_label: str) -> None:
    """Notify that a previously scheduled cancellation has been cleared."""
    _send(
        to=email,
        subject="Your subscription cancellation was reverted",
        html=(
            f"<p>The scheduled cancellation for <strong>{subscription_label}</strong>"
            " has been cleared. The subscription will continue to renew.</p>"
        ),
    )
    logger.info("Subscription cancel-resumed email sent to %s", email)
