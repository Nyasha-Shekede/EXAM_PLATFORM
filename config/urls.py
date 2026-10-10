from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from .health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(
            html_email_template_name="registration/password_reset_email_html.html",
            extra_email_context={
                "site_name": getattr(settings, "SITE_NAME", "Drone Academy"),
                "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
            },
        ),
        name="password_reset",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("exams.urls")),
]

