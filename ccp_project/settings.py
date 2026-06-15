import os
from pathlib import Path
import copy
from django.template import context

# Python 3.14 compatibility monkeypatch for Django 4.2 template context copying
def base_context_copy(self):
    duplicate = context.BaseContext()
    duplicate.__class__ = self.__class__
    duplicate.__dict__ = copy.copy(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate

def context_copy(self):
    duplicate = base_context_copy(self)
    duplicate.render_context = copy.copy(self.render_context)
    return duplicate

context.BaseContext.__copy__ = base_context_copy
context.Context.__copy__ = context_copy

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-h^52rm#acw))4_ja$k8k5#b5oforfv7&tok#+dpyrb-xvyhe%v')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,13.49.229.197,csaconline.in,www.csaconline.in').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'admissions',
    'courses',
    'admin_panel',
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

ROOT_URLCONF = 'ccp_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.site_footer_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ccp_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SQL Server connection for data import
MSSQL_SERVER = os.getenv('MSSQL_SERVER', r'.\SQLEXPRESS')
MSSQL_CCPDB = os.getenv('MSSQL_CCPDB', 'ccpdb')
MSSQL_COURSEDB = os.getenv('MSSQL_COURSEDB', 'courseinformation')
MSSQL_TRUSTED_CONNECTION = os.getenv('MSSQL_TRUSTED_CONNECTION', 'yes').lower() in ('1', 'true', 'yes')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

SESSION_COOKIE_AGE = 3600
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

LOGIN_URL = '/login/'
STUDENT_SESSION_KEY = 'student_reg_no'