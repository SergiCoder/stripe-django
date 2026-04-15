"""Celery tasks for the orgs app."""

from __future__ import annotations

import logging
from uuid import UUID

import stripe

from config.celery import app

logger = logging.getLogger(__name__)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def send_invitation_email_task(email: str, token: str, org_name: str, inviter_name: str) -> None:
    """Send an org invitation email via Resend (async-safe)."""
    from apps.orgs.email import send_invitation_email

    send_invitation_email(email, token, org_name, inviter_name)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def decrement_subscription_seats_task(org_id: str) -> None:
    """Decrement a team subscription's seat count after a member was removed."""
    from apps.orgs.services import decrement_subscription_seats

    decrement_subscription_seats(UUID(org_id))


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def cancel_stripe_subs_task(stripe_sub_ids: list[str], org_id: str) -> None:
    """Cancel a batch of Stripe subscriptions off the request path (post org delete)."""
    for sub_id in stripe_sub_ids:
        try:
            stripe.Subscription.cancel(sub_id)
        except stripe.StripeError:
            logger.exception(
                "Failed to cancel Stripe sub %s for org %s",
                sub_id,
                org_id,
            )
