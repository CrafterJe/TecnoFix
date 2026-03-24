from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ['debug_toolbar']  # noqa
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa

INTERNAL_IPS = ['127.0.0.1', '::1']

# Show SQL queries in console
LOGGING['loggers']['django.db.backends'] = {  # noqa
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}
