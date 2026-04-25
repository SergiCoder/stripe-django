"""Drop the dual-shape Subscription: delete free rows, drop the free-only constraint.

Subscription becomes a pure Stripe mirror — every row has a stripe_id. The free
tier is now represented by the *absence* of a Subscription rather than a row
with stripe_id IS NULL. Existing free Subscription rows and their seeded
free Plan are removed; the partial unique constraint that guarded "at most one
free sub per user" is dropped because no free rows exist any more.
"""

from __future__ import annotations

from typing import Any

from django.db import migrations


def _delete_free_rows(apps: Any, schema_editor: Any) -> None:  # noqa: ANN401, ARG001
    Subscription = apps.get_model("billing", "Subscription")
    Plan = apps.get_model("billing", "Plan")

    # Free Subscriptions are exactly the rows without a Stripe id.
    Subscription.objects.filter(stripe_id__isnull=True).delete()

    # Free Plan rows (tier=1, context="personal") become unreachable once
    # assign_free_plan and the free seed entry are gone in the next commit;
    # delete them now while no Subscription still references them. PROTECT FK
    # on Subscription.plan would block this if any free sub still existed.
    Plan.objects.filter(tier=1, context="personal").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0013_creditbalance_credittransaction"),
    ]

    operations = [
        migrations.RunPython(_delete_free_rows, reverse_code=migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="subscription",
            name="uniq_free_subscription_per_user",
        ),
    ]
