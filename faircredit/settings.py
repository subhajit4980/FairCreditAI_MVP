"""
Django settings for FairCreditScore prototype.
"""

import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env (simple parser; avoids adding python-dotenv as a hard dependency).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _sep, _value = _line.partition("=")
        os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-@j)tsl6vd0a&n9s8^n42!u%ufb-&yqv0(=rva5uvgei5d%fkvi",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]
# Heroku terminates TLS at the router and forwards via X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # LocaleMiddleware must sit after SessionMiddleware (reads the session) and
    # before CommonMiddleware (which uses the active language for URLs).
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "faircredit.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "faircredit.wsgi.application"

# Database resolution order:
#   1. DATABASE_URL (Heroku / dj-database-url)
#   2. POSTGRES_* env vars
#   3. SQLite fallback for local prototype work
if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            ssl_require=os.environ.get("DATABASE_SSL", "1") == "1",
        )
    }
elif os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", os.environ.get("POSTGRES_DB", "")),
            "USER": os.environ.get("DB_USER", os.environ.get("POSTGRES_USER", "postgres")),
            "PASSWORD": os.environ.get("DB_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "")),
            "HOST": os.environ.get("DB_HOST", os.environ.get("POSTGRES_HOST", "localhost")),
            "PORT": os.environ.get("DB_PORT", os.environ.get("POSTGRES_PORT", "5432")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "post_login_redirect"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Languages offered by the portal (issue #13). English is the source language;
# the others have message catalogs under ``locale/<code>/LC_MESSAGES/``.
LANGUAGES = [
    ("en", _("English")),
    ("hi", _("Hindi")),
    ("bn", _("Bengali")),
    ("mr", _("Marathi")),
    ("te", _("Telugu")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

FINBOX_UAT_BASE_URL = os.environ.get("FINBOX_UAT_BASE_URL", "https://apis-uat.bankconnect.finbox.in")
FINBOX_PROD_BASE_URL = os.environ.get("FINBOX_PROD_BASE_URL", "https://apis.bankconnect.finbox.in")
FINBOX_UAT_API_KEY = os.environ.get("FINBOX_UAT_API_KEY", "VUWvcQZ4TRi3Ylpvazah2CuamS0xUxxi6zFmPb8w")
FINBOX_UAT_SERVER_HASH = os.environ.get("FINBOX_UAT_SERVER_HASH", "a8017c902a444b7f8613fa88e2013034")
FINBOX_PROD_API_KEY = os.environ.get("FINBOX_PROD_API_KEY", "wOK0Ra3Sn0QGmPl02cNl3qLfkhyaeXxNjQa0c0PC")
FINBOX_PROD_SERVER_HASH = os.environ.get("FINBOX_PROD_SERVER_HASH", "d0ddf3f57aaa463bbb4e87809c1d0edb")
