import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# CSRF Trusted Origins - required for HTTPS sites
# Check if CSRF_TRUSTED_ORIGINS is explicitly set
csrf_origins_env = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_env.split(",") if origin.strip()]
else:
    # Derive from ALLOWED_HOSTS
    CSRF_TRUSTED_ORIGINS = []
    for host in ALLOWED_HOSTS:
        host = host.strip()
        if host and host != "*":
            # Add https for production
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")
            # Add http for local development
            if DEBUG:
                CSRF_TRUSTED_ORIGINS.append(f"http://{host}")
    
    # Always add localhost for development
    if DEBUG:
        CSRF_TRUSTED_ORIGINS.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost",
            "http://127.0.0.1"
        ])

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

# Debug CSRF settings (remove in production if needed)
if DEBUG:
    print(f"DEBUG: ALLOWED_HOSTS = {ALLOWED_HOSTS}")
    print(f"DEBUG: CSRF_TRUSTED_ORIGINS = {CSRF_TRUSTED_ORIGINS}")

