import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_SECRET_KEY_DEFAULT = "id9-*c7ki%=9!o=pxx#_d3nt)eim-!)y5=knuw4b9=attnug&-"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _SECRET_KEY_DEFAULT)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

if not DEBUG:
    if SECRET_KEY == _SECRET_KEY_DEFAULT:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set to a strong secret in production."
        )
    if not os.environ.get("DJANGO_ALLOWED_HOSTS"):
        raise ImproperlyConfigured(
            "DJANGO_ALLOWED_HOSTS must be explicitly set in production."
        )

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

# Comma-separated list of trusted reverse proxy IPs.
# Only requests from these IPs will have X-Forwarded-For trusted.
TRUSTED_PROXIES = set(
    ip.strip()
    for ip in os.environ.get("TRUSTED_PROXIES", "").split(",")
    if ip.strip()
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "users",
    "projects",
    "tasks",
    "analytics",
    "realtime",
]

SPECTACULAR_SETTINGS = {
    "TITLE": "Dodoist API",
    "DESCRIPTION": "Task and project management API combining personal todos with Scrum/Kanban workflows.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "tasks.authentication.SessionTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user":                 "1000/minute",
        "login":                "5/minute",
        "register":             "10/hour",
        "forgot_password":      "5/hour",
        "reset_password":       "5/hour",
        "verify_email":         "10/hour",
        "resend_verification":  "5/hour",
        "comment_write":        "60/hour",
        "reaction_write":       "120/hour",
        "attachment_upload":    "100/hour",
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

# ---------------------------------------------------------------------------
# HTTPS / security flags (production only)
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
# JS must be able to read the CSRF cookie to send it in the X-CSRFToken header.
CSRF_COOKIE_HTTPONLY = False

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:4200",
    ).split(",")
    if origin.strip()
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

ROOT_URLCONF = "dodoist.urls"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ---------------------------------------------------------------------------
# CORS — allow the Angular dev server (and production origins from env)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    *[
        o.strip()
        for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ],
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    # Verification token still sent as header (stateless, no auth required)
    "x-verification-token",
]

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Dodoist <noreply@dodoist.com>")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:4200")

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

_broker_default = "memory://" if DEBUG else os.environ.get("CELERY_BROKER_URL", "")
if not DEBUG and not os.environ.get("CELERY_BROKER_URL"):
    raise ImproperlyConfigured("CELERY_BROKER_URL must be set in production.")

_result_default = "cache+memory://" if DEBUG else os.environ.get("CELERY_RESULT_BACKEND", "")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", _broker_default)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", _result_default)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# In dev (DEBUG=True) run tasks synchronously so no broker is needed.
_eager_default = "true" if DEBUG else "false"
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_ALWAYS_EAGER", _eager_default).lower() == "true"
# Only propagate task exceptions in eager/dev mode — production swallows and retries.
CELERY_TASK_EAGER_PROPAGATES = DEBUG

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "dodoist": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
