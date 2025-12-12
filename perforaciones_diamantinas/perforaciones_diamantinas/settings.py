import os
from pathlib import Path
import environ

env = environ.Env(DEBUG=(bool, False))

BASE_DIR = Path(__file__).resolve().parent.parent

# Leer archivo .env
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-in-production')
DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Permitir subdominios de ngrok en desarrollo para exponer el servidor local
# de forma temporal. Esto solo se activa cuando DEBUG=True.
if DEBUG:
    if '.ngrok.io' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('.ngrok.io')

# Orígenes confiables para CSRF. Se puede ampliar desde .env si se desea.
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['http://localhost', 'http://127.0.0.1'])
if DEBUG:
    # Permitir orígenes https de ngrok (subdominios)
    if 'https://*.ngrok.io' not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append('https://*.ngrok.io')
    # Agregar variantes de localhost con puerto
    for port in [8000, 8080]:
        origin = f'http://localhost:{port}'
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
        origin = f'http://127.0.0.1:{port}'
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

# Configuraciones adicionales de CSRF para desarrollo
if DEBUG:
    CSRF_COOKIE_SECURE = False  # No requiere HTTPS en desarrollo
    CSRF_COOKIE_HTTPONLY = False  # Permite JavaScript acceso en desarrollo
    CSRF_COOKIE_SAMESITE = 'Lax'  # Menos restrictivo para desarrollo
    SESSION_COOKIE_SECURE = False  # No requiere HTTPS en desarrollo
    SESSION_COOKIE_SAMESITE = 'Lax'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drilling',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware personalizado
    'drilling.middleware.ContractSecurityMiddleware',
    'drilling.middleware.RoleBasedTemplateMiddleware',  # Asigna template según rol
    # 'drilling.middleware.LoginRequiredMiddleware',  # Opcional - descomenta si quieres forzar login en todas las URLs
]
ROOT_URLCONF = 'perforaciones_diamantinas.urls'

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
                'drilling.context_processors.base_template',  # Template según rol
            ],
        },
    },
]

WSGI_APPLICATION = 'perforaciones_diamantinas.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='neondb'),
        'USER': env('DB_USER', default='neondb_owner'),
        'PASSWORD': env('DB_PASSWORD', default='npg_Athe0VmqL6cI'),
        'HOST': env('DB_HOST', default='ep-winter-bread-achugblw-pooler.sa-east-1.aws.neon.tech'),
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'drilling.CustomUser'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'


FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

# Configuración de Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@vilbragroup.com')

# Configuración de tokens de activación (24 horas)
ACTIVATION_TOKEN_EXPIRY_HOURS = 24

# Configuración de APIs externas Vilbragroup TIC
VILBRAGROUP_API_TOKEN = env('VILBRAGROUP_API_TOKEN', default='cff25a36-682a-4570-ad84-aaaabffc89bf')
CENTRO_COSTO_DEFAULT = env('CENTRO_COSTO_DEFAULT', default='000003')

# Logging para APIs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'drilling.api_client': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}