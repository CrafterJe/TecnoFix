from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

INSTALLED_APPS += ['debug_toolbar']  # noqa
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa

INTERNAL_IPS = ['127.0.0.1', '::1']

LOGGING['loggers']['core'] = {  # noqa
    'handlers': ['file'],
    'level': 'INFO',
    'propagate': False,
}

LOGGING['loggers']['django.server'] = {  # noqa
    'handlers': ['console'],
    'level': 'INFO',
    'propagate': False,
}
