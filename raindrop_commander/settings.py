import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# CSRF Trusted Origins - required for HTTPS sites
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []
# If CSRF_TRUSTED_ORIGINS is not set, derive from ALLOWED_HOSTS
if not CSRF_TRUSTED_ORIGINS or CSRF_TRUSTED_ORIGINS == ['']:
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host and host != "*"]
    # Also add http for local development
    if DEBUG:
        CSRF_TRUSTED_ORIGINS.extend([f"http://{host}" for host in ALLOWED_HOSTS if host and host != "*"])
        CSRF_TRUSTED_ORIGINS.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "commander",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add WhiteNoise for static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "raindrop_commander.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "raindrop_commander.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# WhiteNoise configuration for static files
# Use basic storage to avoid manifest issues in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

