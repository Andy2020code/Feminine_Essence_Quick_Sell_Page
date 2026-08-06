# /core/context_processors.py

def csp_nonce(request):
    """
    Make CSP nonce available in every Django template automatically.
    Add to TEMPLATES['OPTIONS']['context_processors'] in settings.
    """
    return {
        'csp_nonce': getattr(request, 'csp_nonce', ''),
    }