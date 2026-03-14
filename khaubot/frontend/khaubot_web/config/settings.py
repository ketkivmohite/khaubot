import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-7s(9mj^=zg5ow#!!5%b$lx6@6a0=mr7#e@r986l@ubc38%*&%r",
)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"


allowed_hosts_env = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,.vercel.app",
)
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]


csrf_trusted_origins_env = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://*.vercel.app",
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_trusted_origins_env.split(",") if origin.strip()
]


# ───────────────── Apps ─────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "crispy_forms",
    "crispy_tailwind",

    "core",
]


# ───────────────── Middleware ─────────────────

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


# ───────────────── Templates ─────────────────

TEMPLATES = [
{
    "BACKEND": "django.template.backends.django.DjangoTemplates",

    "DIRS": [
        BASE_DIR / "templates",
        BASE_DIR / "core" / "templates"
    ],

    "APP_DIRS": True,

    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]


# ───────────────── Database ─────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ───────────────── Sessions ─────────────────

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ───────────────── Static Files ─────────────────

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}


# ───────────────── Crispy Forms ─────────────────

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"


# ───────────────── FastAPI Backend URL ─────────────────

KHAUBOT_API_URL = os.getenv(
    "KHAUBOT_API_URL",
    "http://127.0.0.1:8001"
)


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"