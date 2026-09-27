import os
from pathlib import Path
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","exams"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.template.context_processors.media","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","exams.context.site"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR/'db.sqlite3'}", conn_max_age=60)}
AUTH_PASSWORD_VALIDATORS = [{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="en-gb"
TIME_ZONE=os.getenv("TIME_ZONE","Africa/Harare")
USE_I18N=True
USE_TZ=True
STATIC_URL="static/"
STATIC_ROOT=BASE_DIR/"staticfiles"
STATICFILES_DIRS=[BASE_DIR/"static"]
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":("django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "whitenoise.storage.CompressedManifestStaticFilesStorage")}}
MEDIA_URL="/protected-media/"
MEDIA_ROOT=BASE_DIR/"media"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_REDIRECT_URL="dashboard"
LOGOUT_REDIRECT_URL="login"
SITE_NAME=os.getenv("SITE_NAME","Local Drone Academy")
SUPPORT_EMAIL=os.getenv("SUPPORT_EMAIL","training@example.test")
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0" if DEBUG else "1") == "1"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "0" if DEBUG else "1") == "1"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "0" if DEBUG else "1") == "1"
SECURE_HSTS_SECONDS=int(os.getenv("SECURE_HSTS_SECONDS","31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS=os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS","1") == "1"
SECURE_HSTS_PRELOAD=os.getenv("SECURE_HSTS_PRELOAD","0") == "1"
SECURE_REFERRER_POLICY="same-origin"
X_FRAME_OPTIONS="DENY"
FILE_UPLOAD_MAX_MEMORY_SIZE=8*1024*1024
DATA_UPLOAD_MAX_MEMORY_SIZE=12*1024*1024

AUTHENTICATION_BACKENDS=["exams.auth.UsernameOrEmailBackend"]
