# config/settings/development.py

from .settings import *

DEBUG = True


# Use report-only mode in development
CSP_REPORT_ONLY = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}