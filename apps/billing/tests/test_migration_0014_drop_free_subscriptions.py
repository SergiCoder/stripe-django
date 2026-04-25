"""Test the data-deletion path of migration 0014_drop_free_subscriptions.

The migration removes free Subscription rows (stripe_id IS NULL) and the
free personal Plan they referenced. The test runner re-runs migrations from
scratch on each test DB, so the data step never actually has rows to delete
in normal test runs — this test exercises it explicitly by seeding rows
against the historical 0013 schema, then forward-migrating to 0014.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def _run_executor(target: list[tuple[str, str]]) -> None:
    """Migrate the test DB to *target* using a freshly-loaded executor."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)


@pytest.mark.django_db(transaction=True)
class TestMigration0014DropFreeSubscriptions:
    """0014 deletes free Subscription rows + the seeded free personal Plan."""

    def setup_method(self) -> None:
        # Migrate back to the state immediately before 0014 so we can seed
        # rows that the partial unique constraint (added in 0012) still
        # allows: at most one free sub per user.
        _run_executor([("billing", "0013_creditbalance_credittransaction")])

    def teardown_method(self) -> None:
        # Restore the head state so subsequent tests aren't left on 0013.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        latest = max(
            (name for app, name in executor.loader.graph.leaf_nodes() if app == "billing"),
        )
        _run_executor([("billing", latest)])

    def test_forward_deletes_free_subscriptions_and_free_plan(self, django_user_model):
        """Forward-migrating 0014 deletes free Subscription rows + the free Plan."""
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        old_apps = executor.loader.project_state(
            [("billing", "0013_creditbalance_credittransaction")]
        ).apps

        Plan = old_apps.get_model("billing", "Plan")
        Subscription = old_apps.get_model("billing", "Subscription")

        free_plan = Plan.objects.create(
            name="Personal Free",
            context="personal",
            tier=1,
            interval="month",
            is_active=True,
        )
        paid_plan = Plan.objects.create(
            name="Personal Pro",
            context="personal",
            tier=3,
            interval="month",
            is_active=True,
        )
        team_free_lookalike = Plan.objects.create(
            # tier=1 but context="team" — must NOT be deleted; the migration
            # filters tier=1 AND context="personal" specifically.
            name="Team Lookalike",
            context="team",
            tier=1,
            interval="month",
            is_active=True,
        )

        user_a = django_user_model.objects.create_user(email="a@example.com", full_name="A")
        user_b = django_user_model.objects.create_user(email="b@example.com", full_name="B")

        # Two free subs (one per user — partial unique constraint allows that)
        # plus one paid sub that must survive.
        free_sub_a = Subscription.objects.create(
            stripe_id=None,
            user_id=user_a.id,
            status="active",
            plan=free_plan,
            quantity=1,
            current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
            current_period_end=datetime(9999, 12, 31, tzinfo=UTC),
        )
        free_sub_b = Subscription.objects.create(
            stripe_id=None,
            user_id=user_b.id,
            status="active",
            plan=free_plan,
            quantity=1,
            current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
            current_period_end=datetime(9999, 12, 31, tzinfo=UTC),
        )
        paid_sub = Subscription.objects.create(
            stripe_id="sub_paid_keepme",
            user_id=user_a.id,
            status="active",
            plan=paid_plan,
            quantity=1,
            current_period_start=datetime(2026, 1, 1, tzinfo=UTC),
            current_period_end=datetime(2026, 2, 1, tzinfo=UTC),
        )

        # Forward-migrate to 0014 — this runs _delete_free_rows.
        _run_executor([("billing", "0014_drop_free_subscriptions")])

        new_apps = (
            MigrationExecutor(connection)
            .loader.project_state([("billing", "0014_drop_free_subscriptions")])
            .apps
        )
        SubscriptionAfter = new_apps.get_model("billing", "Subscription")  # noqa: N806  # historical model class binding
        PlanAfter = new_apps.get_model("billing", "Plan")  # noqa: N806  # historical model class binding

        # Free subs are gone, paid sub is preserved.
        remaining_subs = set(SubscriptionAfter.objects.values_list("pk", flat=True))
        assert free_sub_a.pk not in remaining_subs
        assert free_sub_b.pk not in remaining_subs
        assert paid_sub.pk in remaining_subs

        # Free personal Plan is gone; paid personal Plan and team lookalike remain.
        remaining_plans = set(PlanAfter.objects.values_list("pk", flat=True))
        assert free_plan.pk not in remaining_plans
        assert paid_plan.pk in remaining_plans
        assert team_free_lookalike.pk in remaining_plans

    def test_forward_is_idempotent_when_no_free_rows_exist(self):
        """Re-running on a clean DB (the normal test-runner path) is a no-op."""
        # No seeding — just forward-migrate. Should not raise.
        _run_executor([("billing", "0014_drop_free_subscriptions")])

        new_apps = (
            MigrationExecutor(connection)
            .loader.project_state([("billing", "0014_drop_free_subscriptions")])
            .apps
        )
        SubscriptionAfter = new_apps.get_model("billing", "Subscription")  # noqa: N806  # historical model class binding
        assert SubscriptionAfter.objects.count() == 0
