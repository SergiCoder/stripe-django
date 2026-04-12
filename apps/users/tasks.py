"""Celery tasks for user account operations."""

from __future__ import annotations

import logging
from uuid import UUID

from asgiref.sync import async_to_sync, sync_to_async

from config.celery import app

logger = logging.getLogger(__name__)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def send_verification_email_task(email: str, token: str) -> None:
    """Send email verification link via Resend (async-safe)."""
    from apps.users.email import send_verification_email

    send_verification_email(email, token)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def send_password_reset_email_task(email: str, token: str) -> None:
    """Send password reset link via Resend (async-safe)."""
    from apps.users.email import send_password_reset_email

    send_password_reset_email(email, token)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def process_scheduled_deletions() -> None:
    """Hard-delete users whose scheduled_deletion_at has passed."""
    from saasmint_core.services.gdpr import execute_account_deletion

    from apps.billing.repositories import (
        DjangoStripeCustomerRepository,
        DjangoSubscriptionRepository,
    )
    from apps.users.repositories import DjangoUserRepository

    user_repo = DjangoUserRepository()
    customer_repo = DjangoStripeCustomerRepository()
    subscription_repo = DjangoSubscriptionRepository()

    pending_users = async_to_sync(user_repo.list_pending_deletions)()

    async def _pre_delete(user_id: UUID) -> None:
        from apps.orgs.models import OrgMember
        from apps.orgs.services import decrement_subscription_seats, delete_orgs_created_by_user

        # If owner: delete owned orgs (cascades member account deletion)
        await sync_to_async(delete_orgs_created_by_user)(user_id)
        # If non-owner member: remove from org + decrement seats
        membership = await OrgMember.objects.filter(user_id=user_id).afirst()
        if membership:
            org_id = membership.org_id
            await membership.adelete()
            await sync_to_async(decrement_subscription_seats)(org_id)

    for user in pending_users:
        try:
            async_to_sync(execute_account_deletion)(
                user_id=user.id,
                user_repo=user_repo,
                customer_repo=customer_repo,
                subscription_repo=subscription_repo,
                pre_delete_hook=_pre_delete,
            )
            logger.info("Executed scheduled deletion for user %s", user.id)
        except Exception:
            logger.exception("Failed scheduled deletion for user %s", user.id)


@app.task  # type: ignore[untyped-decorator]  # celery has no stubs
def cleanup_orphaned_org_accounts() -> None:
    """Delete org_member accounts that never completed checkout.

    Targets users with account_type=ORG_MEMBER who have no org membership
    and were created more than 24 hours ago.
    """
    from datetime import UTC, datetime, timedelta

    from apps.orgs.models import OrgMember
    from apps.users.models import AccountType, User

    cutoff = datetime.now(UTC) - timedelta(hours=24)
    orphans = User.objects.filter(
        account_type=AccountType.ORG_MEMBER,
        created_at__lt=cutoff,
        deleted_at__isnull=True,
    ).exclude(
        id__in=OrgMember.objects.values_list("user_id", flat=True),
    )
    count = orphans.count()
    if count:
        orphans.delete()
        logger.info("Cleaned up %d orphaned org-member accounts", count)
