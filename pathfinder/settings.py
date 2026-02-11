import os
from pathlib import Path
from decimal import Decimal

import environ

BASE_DIR = Path(__file__).resolve().parent

env = environ.Env(
    DJANGO_SECRET_KEY=(str, "dev-secret"),
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    DATABASE_URL=(str, "postgis://pathfinder:pathfinder@localhost:5432/pathfinder"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    ORS_API_KEY=(str, ""),
    MAPBOX_API_KEY=(str, ""),
    MAPBOX_DIRECTIONS_BASE_URL=(str, "https://api.mapbox.com/directions/v5/mapbox/driving"),
    ORS_DIRECTIONS_URL=(str, "https://api.openrouteservice.org/v2/directions/driving-car"),
    MAPBOX_GEOCODING_BASE_URL=(str, "https://api.mapbox.com/geocoding/v5/mapbox.places"),
    ORS_GEOCODING_URL=(str, "https://api.openrouteservice.org/geocode/search"),
    INGEST_GEOCODE=(bool, True),
    VEHICLE_MAX_RANGE_MILES=(float, 500.0),
    VEHICLE_MPG=(str, "10"),
)

environ.Env.read_env(str(BASE_DIR.parent / ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS") if isinstance(env("ALLOWED_HOSTS"), str) else env("ALLOWED_HOSTS")
REDIS_URL = env("REDIS_URL")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "ingest",
    "routing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pathfinder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "pathfinder.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL")
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Pathfinder Fuel Optimization API",
    "DESCRIPTION": "Routing with optimal fuel stops and cost minimization",
    "VERSION": "1.0.0",
}

CORS_ALLOW_ALL_ORIGINS = True

# Celery
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_TASK_TIME_LIMIT = 60 * 10
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 8

ORS_API_KEY = env("ORS_API_KEY")
MAPBOX_API_KEY = env("MAPBOX_API_KEY")
MAPBOX_DIRECTIONS_BASE_URL = env("MAPBOX_DIRECTIONS_BASE_URL")
ORS_DIRECTIONS_URL = env("ORS_DIRECTIONS_URL")
MAPBOX_GEOCODING_BASE_URL = env("MAPBOX_GEOCODING_BASE_URL")
ORS_GEOCODING_URL = env("ORS_GEOCODING_URL")
INGEST_GEOCODE = env.bool("INGEST_GEOCODE", default=True)
VEHICLE_MAX_RANGE_MILES = env.float("VEHICLE_MAX_RANGE_MILES", default=500.0)
VEHICLE_MPG = Decimal(env("VEHICLE_MPG", default="10"))

# GeoDjango
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
PROJ_LIBRARY_PATH = env("PROJ_LIBRARY_PATH", default=None)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "ingest": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "routing": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "pathfinder": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
