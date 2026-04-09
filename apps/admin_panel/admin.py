"""Extended Django admin — re-registers User with subscription status column and sets site_url to /dashboard/."""  # noqa: E501

from typing import ClassVar

from django.contrib import admin
from django.db.models import OuterRef, Q, QuerySet, Subquery
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString

from apps.billing.models import ACTIVE_SUBSCRIPTION_STATUSES, Subscription, SubscriptionStatus
from apps.users.admin import UserAdmin
from apps.users.models import User

admin.site.site_url = "/dashboard/"

# Re-register User admin to show subscription status
admin.site.unregister(User)


class DeletionStateFilter(admin.SimpleListFilter):
    """Filter users by GDPR deletion state (active / pending deletion / deleted)."""

    title = "deletion state"
    parameter_name = "deletion_state"

    def lookups(
        self,
        request: HttpRequest,
        model_admin: admin.ModelAdmin,  # type: ignore[type-arg]
    ) -> list[tuple[str, str]]:
        return [
            ("active", "Active (not deleted)"),
            ("pending", "Pending deletion"),
            ("deleted", "Deleted"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        value = self.value()
        if value == "active":
            return queryset.filter(deleted_at__isnull=True, scheduled_deletion_at__isnull=True)
        if value == "pending":
            return queryset.filter(deleted_at__isnull=True, scheduled_deletion_at__isnull=False)
        if value == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


@admin.register(User)
class UserAdminExtended(UserAdmin):  # type: ignore[type-arg]  # django-stubs ModelAdmin is generic but UserAdmin inherits from BaseUserAdmin which doesn't declare its type parameter
    list_display = (
        "email",
        "full_name",
        "account_type",
        "subscription_status",
        "is_verified",
        "is_active",
        "scheduled_deletion_at",
        "deleted_at",
        "created_at",
    )
    list_filter: ClassVar[tuple[object, ...]] = (
        DeletionStateFilter,
        "account_type",
        "is_active",
        "is_staff",
        "is_verified",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        qs = super().get_queryset(request)  # type: ignore[misc]  # django-stubs types get_queryset as returning QuerySet[Any]; we narrow to QuerySet[User]
        customer_sub = Subscription.objects.filter(
            Q(user=OuterRef("pk")) | Q(stripe_customer__user=OuterRef("pk")),
            status__in=ACTIVE_SUBSCRIPTION_STATUSES,
        ).order_by("-created_at")
        return qs.annotate(_subscription_status=Subquery(customer_sub.values("status")[:1]))

    @admin.display(description="Subscription")
    def subscription_status(self, obj: User) -> str | SafeString:
        status = getattr(obj, "_subscription_status", None)
        if not status:
            return "—"
        colour = {
            SubscriptionStatus.ACTIVE: "green",
            SubscriptionStatus.TRIALING: "blue",
            SubscriptionStatus.PAST_DUE: "orange",
        }.get(status, "grey")
        return format_html('<span style="color:{}">{}</span>', colour, status)
