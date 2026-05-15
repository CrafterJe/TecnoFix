import os

from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# Persistir la conexión MySQL entre requests en dev (evita handshake TCP por request).
DATABASES['default']['CONN_MAX_AGE'] = 60  # noqa

# Debug toolbar: off por default para no ralentizar dev.
# Para activar: ENABLE_DEBUG_TOOLBAR=1 python manage.py runserver
if os.getenv('ENABLE_DEBUG_TOOLBAR') == '1':
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
