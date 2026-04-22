import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-kvs)^9axtt$*+1&n@6blik7dmg@rq04nnnql_-@kbo36ubwjx+"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "journal.apps.JournalConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "journal.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

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

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lusaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "admin-login"
LOGIN_REDIRECT_URL = "admin-dashboard"
LOGOUT_REDIRECT_URL = "admin-login"

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "kabaghegomezyani@gmail.com")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "kabaghegomezyani@gmail.com")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "fkrnaubwhqmsthgv")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"

HCAPTCHA_SITE_KEY = os.getenv("HCAPTCHA_SITE_KEY", "")
HCAPTCHA_SECRET_KEY = os.getenv("HCAPTCHA_SECRET_KEY", "")
NODEMAILER_ENDPOINT = os.getenv("NODEMAILER_ENDPOINT", "")
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "mumj_articles")
DOI_API_URL = os.getenv("DOI_API_URL", "")
PLAGIARISM_API_URL = os.getenv("PLAGIARISM_API_URL", "")

SITE_NAME = "Mulungushi University Multidisciplinary Journal"
SITE_SHORT_NAME = "MUMJ"
SITE_EMAIL = "journals@mu.ac.zm"
SITE_PHONE = "+260 211 000 000"
SITE_ADDRESS = "Mulungushi University, Great North Road Campus, Kabwe, Zambia"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
