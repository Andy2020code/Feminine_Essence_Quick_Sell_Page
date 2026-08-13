# server/core/context_processors.py
from django.conf import settings

def csp_nonce(request):
    return {
        'csp_nonce': getattr(request, 'csp_nonce', ''),
    }


def static_version(request):
    return {
        'css_version': getattr(settings, 'STATIC_VERSION', '1'),
    }