"""Root URL configuration."""

from apps.dashboard.views import HijackAcquireView, HijackReleaseView
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Override hijack acquire to redirect to dashboard instead of /admin/
    path("hijack/acquire/", HijackAcquireView.as_view(), name="hijack-acquire"),
    path("hijack/release/", HijackReleaseView.as_view(), name="hijack-release"),
    path("hijack/", include("hijack.urls")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("api/v1/account/", include("apps.users.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("api/v1/orgs/", include("apps.orgs.urls")),
    path("api/v1/webhooks/", include("apps.billing.webhook_urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
