import os
from pathlib import Path
from decouple import config, Csv

# --- 1. BASE PATHS ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- 2. CORE SECURITY & ENVIRONMENT ---
DJANGO_ENV = config('DJANGO_ENV', default='development')
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())
csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='https://pgp.pmono.no')
CSRF_TRUSTED_ORIGINS = csrf_origins.split(',') if isinstance(csrf_origins, str) else csrf_origins
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# --- 3. APP DEFINITION ---
INSTALLED_APPS = [
    "app.apps.AppConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Handles static files in prod
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# --- 4. TEMPLATES ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
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

# --- 5. DATABASES ---
if config('DJANGO_ENV', default='development') == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',  
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='db'),  # Docker service name
            'PORT': config('DB_PORT', default='3306'),  
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- 6. AUTHENTICATION & PASSWORDS ---
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
PASSWORD_RESET_TIMEOUT = 259200

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- 7. REGIONAL SETTINGS ---
TIME_ZONE = 'Europe/Oslo'
LANGUAGE_CODE = 'nn' # Nynorsk
USE_I18N = True
USE_TZ = True
TIME_INPUT_FORMATS = ['%H:%M']

# --- 8. EXTERNAL SERVICES (SPOTIFY) ---
SPOTIPY_CLIENT_ID = config('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = config('SPOTIPY_CLIENT_SECRET')
REACT_APP_SPOTIPY_REDIRECT_URI = config('SPOTIPY_REDIRECT_URI')

# --- 9. EMAIL SETTINGS ---
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@yourdomain.com')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD') 

# --- 10. STATIC & MEDIA FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- 11. LOGGING ---
LOG_LEVEL = 'INFO' if DJANGO_ENV == 'production' else 'DEBUG'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}