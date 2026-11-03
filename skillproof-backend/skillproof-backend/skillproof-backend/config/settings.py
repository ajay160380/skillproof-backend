import os
from pathlib import Path
import environ
from datetime import timedelta
import ssl

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
SECRET_KEY = env('SECRET_KEY', default='unsafe-secret-key')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com', 'skillproofi-rouge.vercel.app']
GROQ_API_KEY = env('GROQ_API_KEY', default='')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloudinary_storage',
    'cloudinary',

    # Local apps
    'accounts',
    'network',
    'skills',
    'assessments',
    'assistant',
    'badges',
    'marketplace',
    'resumes',
    'jobs',
    'portfolio',
    'messaging',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files (user uploads like audio recordings)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cloudinary Storage (for persistent file uploads on Render)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default='qf6wbumi'),
    'API_KEY': env('CLOUDINARY_API_KEY', default='274489168274869'),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default='sCPUechTlRmm3hGoTGIuEgEe8Gc'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    'https://skillproof-eight.vercel.app',
    'https://skillproofi-rouge.vercel.app',
]
CORS_ALLOW_CREDENTIALS = True

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# Simple JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

if CELERY_BROKER_URL.startswith('rediss://'):
    CELERY_BROKER_USE_SSL = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }
    CELERY_REDIS_BACKEND_USE_SSL = {
        'ssl_cert_reqs': ssl.CERT_NONE
    }

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
