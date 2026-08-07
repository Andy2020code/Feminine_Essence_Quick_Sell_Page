from django.conf import settings

def csp_nonce(request):
    return {
        'csp_nonce': getattr(request, 'csp_nonce', ''),
    }


def static_version(request):
    return {
        "css_version": settings.STATIC_VERSION,
    }