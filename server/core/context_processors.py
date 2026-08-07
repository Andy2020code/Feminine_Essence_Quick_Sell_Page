from django.conf import settings

def csp_nonce(request):
    return {
        'csp_nonce': getattr(request, 'csp_nonce', ''),
    }

# ✅ Ensure this is here
def static_version(request):
    return {
        'css_version': getattr(settings, 'STATIC_VERSION', '1'),
    }