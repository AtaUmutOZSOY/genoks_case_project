"""
Django settings for testing environment.
Optimized for test performance and isolation.
"""

from .base import *

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'genoks_test',
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'TEST': {
            'NAME': 'test_genoks_test',
        },
        'OPTIONS': {
            'options': '-c default_transaction_isolation=serializable'
        }
    }
}

# Disable migrations for faster test execution
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Cache - use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Email - use console backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Media files - use temporary directory
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

# Static files - disable collection during tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Celery - use eager execution for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging - minimal logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Security settings for tests
SECRET_KEY = 'test-secret-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Disable CSRF for API tests
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.SessionAuthentication',
]

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Disable unnecessary middleware for tests
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'middleware.tenant_middleware.TenantMiddleware',
]

# Disable file storage during tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Time zone for consistent test results
USE_TZ = True
TIME_ZONE = 'UTC'

# Internationalization
USE_I18N = False
USE_L10N = False

# Test database settings
TEST_DATABASE_PREFIX = 'test_'
TEST_SCHEMA_PREFIX = 'test_'

# Performance settings for tests
DATABASE_ROUTERS = []  # Disable custom routing for tests

# Disable debug toolbar for tests
if 'debug_toolbar' in INSTALLED_APPS:
    INSTALLED_APPS.remove('debug_toolbar')

# Remove debug toolbar middleware if present
MIDDLEWARE = [m for m in MIDDLEWARE if 'debug_toolbar' not in m] 