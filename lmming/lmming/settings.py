"""
Django settings for lmming project.

Generated by 'django-admin startproject' using Django 5.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Default env values:
env = environ.Env(
    POSTGRES_DB=(str, "lmming"),
    POSTGRES_USER=(str, "lmming"),
    POSTGRES_PASSWORD=(str, "12345LM"),
    POSTGRES_HOST=(str, "localhost"),
    POSTGRES_PORT=(str, "5432"),
    ARCHIVE_INST=(str, "FAC"),
    MINTER_URL=(str, ""),
    MINTER_AUTH=(str, ""),
    MINTER_ORG_ID=(str, "12345"),
    IIIF_BASE_URL=(str, "https://iiif.example.com"),
    CATALOGUE_BASE_URL=(str, "https://atom.example.com"),
    FM_ARCHIVE_ID=(str, "PostID_Arkivbildare"),
    FM_ORGANISATION_NAME=(str, "Organisation"),
    FM_COUNTY=(str, "Distrikt län"),
    FM_MUNICIPALITY=(str, "Kommun"),
    FM_CITY=(str, "Ort"),
    FM_PARISH=(str, "Socken"),
    FM_NAD_LINK=(str, "NAD_LINK"),
    REDIS_HOST=(str, "redis://localhost"),
    REDIS_PORT=(str, "6379"),
    HF_CRINA_HASH=(str, "88870df625e5abfb36c2ecfe2273b6f1a328f43b"),
    HF_KB_HASH=(str, "8e1e0bdcacc4dc230d2199de47b61ce9cac321c7")
)

environ.Env.read_env(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = ["127.0.0.1", "0.0.0.0", "localhost"]

# Application definition

INSTALLED_APPS = [
    'metadata.apps.MetadataConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_bootstrap5',
    'fontawesomefree'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lmming.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lmming.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env("POSTGRES_DB"),
        'USER': env("POSTGRES_USER"),
        'PASSWORD': env("POSTGRES_PASSWORD"),
        'HOST': env("POSTGRES_HOST"),
        'PORT': env("POSTGRES_PORT")
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'CET'

USE_I18N = False  # TODO: revisit this decision ...

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/django_static/"
STATIC_ROOT = BASE_DIR / "django_static"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env("REDIS_PORT")

CELERY_BROKER_URL = f"{REDIS_HOST}:{REDIS_PORT}"  # os.environ.get("REDIS", "redis://localhost:6379")
CELERY_RESULT_BACKEND = f"{REDIS_HOST}:{REDIS_PORT}"  # os.environ.get("REDIS", "redis://localhost:6379")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / Path(env("MEDIA_PATH"))  # BASE_DIR / "media"

NER_BASE_DIR = BASE_DIR.parent / "ner_data"

ARCHIVE_INST = env("ARCHIVE_INST")
MINTER_URL = env("MINTER_URL")
MINTER_AUTH = env("MINTER_AUTH")
MINTER_ORG_ID = env("MINTER_ORG_ID")
IIIF_BASE_URL = env("IIIF_BASE_URL")
CATALOGUE_BASE_URL = env("CATALOGUE_BASE_URL")
FM_ARCHIVE_ID = env("FM_ARCHIVE_ID")
FM_ORGANISATION_NAME = env("FM_ORGANISATION_NAME")
FM_COUNTY = env("FM_COUNTY")
FM_MUNICIPALITY = env("FM_MUNICIPALITY")
FM_CITY = env("FM_CITY")
FM_PARISH = env("FM_PARISH")
FM_NAD_LINK = env("FM_NAD_LINK")

HF_CRINA_HASH = env("HF_CRINA_HASH")
HF_KB_HASH = env("HF_KB_HASH")

SERVER_LOG_NAME = "lmming"
WORKER_LOG_NAME = "lmming_celery"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        SERVER_LOG_NAME: {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        WORKER_LOG_NAME: {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
