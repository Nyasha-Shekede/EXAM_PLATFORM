import os
from pathlib import Path
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
# Render supplies these variables; local development remains opt-in and disposable.
RENDER = os.getenv("RENDER", "").lower() in {"true", "1"}
DEBUG = os.getenv("DEBUG", "0" if RENDER else "1") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "*" if DEBUG else "").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
# Links in emails must be absolute and must not trust an arbitrary request Host.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "").rstrip("/")

INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","exams"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.template.context_processors.media","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","exams.context.site"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR/'db.sqlite3'}", conn_max_age=60, conn_health_checks=True)}
AUTH_PASSWORD_VALIDATORS = [{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="en-gb"
TIME_ZONE=os.getenv("TIME_ZONE","Africa/Harare")
USE_I18N=True
USE_TZ=True
STATIC_URL="/static/"
STATIC_ROOT=BASE_DIR/"staticfiles"
STATICFILES_DIRS=[BASE_DIR/"static"]
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":("django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "whitenoise.storage.CompressedManifestStaticFilesStorage")}}
MEDIA_URL="/protected-media/"
MEDIA_ROOT=Path(os.getenv("MEDIA_ROOT", str(BASE_DIR/"media")))
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_REDIRECT_URL="dashboard"
LOGOUT_REDIRECT_URL="login"
SITE_NAME = os.getenv("SITE_NAME", "Africa Drone Kings")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "training@africadronekings.com")
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
# Render may probe the service over internal HTTP; only the non-sensitive health URL is exempt.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0" if DEBUG else "1") == "1"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0" if DEBUG else "1") == "1"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0" if DEBUG else "1") == "1"
SECURE_HSTS_SECONDS=int(os.getenv("SECURE_HSTS_SECONDS","31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS=os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS","1") == "1"
SECURE_HSTS_PRELOAD=os.getenv("SECURE_HSTS_PRELOAD","0") == "1"
SECURE_REFERRER_POLICY="same-origin"
X_FRAME_OPTIONS="DENY"
FILE_UPLOAD_MAX_MEMORY_SIZE=50*1024*1024
DATA_UPLOAD_MAX_MEMORY_SIZE=50*1024*1024

AUTHENTICATION_BACKENDS=["exams.auth.UsernameOrEmailBackend"]

# Resend uses HTTPS rather than SMTP; console delivery is for local development only.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Africa Drone Kings <training@africadronekings.com>")
EMAIL_BACKEND = "exams.resend_backend.ResendBackend" if RESEND_API_KEY else ("django.core.mail.backends.console.EmailBackend" if DEBUG else "exams.resend_backend.ResendBackend")
# Only use private S3-compatible storage for user uploads on serverless infrastructure.
if os.getenv("AWS_STORAGE_BUCKET_NAME"):
    INSTALLED_APPS += ["storages"]
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage", "OPTIONS": {
        "bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"],
        "access_key": os.environ.get("AWS_ACCESS_KEY_ID"),
        "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "endpoint_url": os.environ.get("AWS_S3_ENDPOINT_URL") or None,
        "region_name": os.environ.get("AWS_S3_REGION_NAME") or None,
        "addressing_style": os.getenv("AWS_S3_ADDRESSING_STYLE", "path" if os.getenv("AWS_S3_ENDPOINT_URL") else "auto"),
        "default_acl": "private", "querystring_auth": True,
        "file_overwrite": False,
    }}

PUBLIC_SIGNUP = os.getenv("PUBLIC_SIGNUP", "1") == "1"
LESSON_UPLOAD_MAX_BYTES = 10 * 1024 * 1024

# Prevent accidental development defaults on the public Render service.
if RENDER:
    from django.core.exceptions import ImproperlyConfigured
    if DEBUG:
        raise ImproperlyConfigured("Set DEBUG=0 on Render")
    if SECRET_KEY == "dev-only-change-me" or len(SECRET_KEY) < 32:
        raise ImproperlyConfigured("Set a strong, stable SECRET_KEY on Render")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS or ".onrender.com" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Use explicit ALLOWED_HOSTS or Render's RENDER_EXTERNAL_HOSTNAME")
    if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise ImproperlyConfigured("Render requires a managed PostgreSQL DATABASE_URL")
    if not os.getenv("AWS_STORAGE_BUCKET_NAME") and not os.getenv("MEDIA_ROOT"):
        raise ImproperlyConfigured("Configure private object storage or MEDIA_ROOT on a persistent Render disk")
    if not RESEND_API_KEY:
        raise ImproperlyConfigured("Set RESEND_API_KEY for production transactional emails")
if PUBLIC_BASE_URL:
    from urllib.parse import urlsplit
    from django.core.exceptions import ImproperlyConfigured
    parsed = urlsplit(PUBLIC_BASE_URL)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ImproperlyConfigured("PUBLIC_BASE_URL must be an origin, e.g. https://academy.example.com")
    if not DEBUG and parsed.scheme != "https":
        raise ImproperlyConfigured("PUBLIC_BASE_URL must use HTTPS in production")
