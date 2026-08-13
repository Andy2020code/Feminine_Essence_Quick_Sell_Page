# core/middleware/csp.py

import secrets
import base64
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class ContentSecurityPolicyMiddleware(MiddlewareMixin):
    """
    Dynamic CSP middleware with per-request nonce generation
    for FeminineEssenceStore.com
    """

    # Directives that support nonce
    NONCE_DIRECTIVES = {'script-src', 'style-src'}

    def process_request(self, request):
        """Generate a unique nonce for each request."""
        request.csp_nonce = self._generate_nonce()

    def process_response(self, request, response):
        """Attach CSP header to every response."""

        # Skip CSP for admin (handled separately) and API endpoints
        if request.path.startswith('/admin/'):
            return response

        nonce = getattr(request, 'csp_nonce', self._generate_nonce())
        policy = self._build_policy(request, nonce)

        header_name = (
            'Content-Security-Policy-Report-Only'
            if getattr(settings, 'CSP_REPORT_ONLY', False)
            else 'Content-Security-Policy'
        )

        response[header_name] = policy
        self._set_additional_headers(response)

        return response

    def _generate_nonce(self) -> str:
        """Generate a cryptographically secure nonce."""
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')

    def _build_policy(self, request, nonce: str) -> str:
        directives = self._get_directives(request, nonce)

        parts = []
        for directive, sources in directives.items():
            if sources:
                parts.append(f"{directive} {' '.join(sources)}")

        # Only add these when NOT in report-only mode
        report_only = getattr(settings, 'CSP_REPORT_ONLY', False)
        if not report_only:
            parts.append('upgrade-insecure-requests')
            parts.append('block-all-mixed-content')

        report_uri = getattr(settings, 'CSP_REPORT_URI', '/csp-report/')
        if report_uri:
            parts.append(f'report-uri {report_uri}')

        return '; '.join(parts)

    def _get_directives(self, request, nonce: str) -> dict:

        def _safe_domain_source(domain: str, scheme: str = "https") -> str | None:
            """Return a CSP source string or None if domain is empty."""
            return f"{scheme}://{domain}" if domain else None

        cdn = getattr(settings, 'CDN_DOMAIN', '')
        domain = getattr(settings, 'DOMAIN', 'feminineessencestore.com')
    
        base_directives = {
            'default-src': ["'self'"],

            'script-src': [
                "'self'",
                f"'nonce-{nonce}'",
                'https://js.stripe.com',
                'https://www.paypal.com',
                'https://*.paypal.com',
                'https://pagead2.googlesyndication.com',
                'https://www.googletagmanager.com',
                'https://www.google-analytics.com',
                'https://www.googleadservices.com',
                'https://connect.facebook.net',
            ],

            'style-src': [
                "'self'",
                f"'nonce-{nonce}'",
                'https://fonts.googleapis.com',
            ],

            # Allows inline style="..." attributes injected by Google Ads
            'style-src-attr': [
                "'unsafe-inline'",
            ],

            'img-src': list(filter(None, [
                "'self'",
                'data:',
                'blob:',
                'https:',
                _safe_domain_source(cdn),          # None entries filtered out
            ])),

            'font-src': [
                "'self'",
                'https://fonts.gstatic.com',
                'data:',
            ],

            'connect-src': [
                "'self'",
                'https://api.stripe.com',
                'https://*.paypal.com',
                'https://www.googletagmanager.com',
                'https://pagead2.googlesyndication.com',
                'https://googleads.g.doubleclick.net',
                'https://www.google-analytics.com',
                'https://analytics.google.com',
                'https://stats.g.doubleclick.net',
                'https://www.google.com',
                'https://ad.doubleclick.net',
                'https://www.googleadservices.com',
                'https://ep1.adtrafficquality.google',       # ← added
                'https://ep2.adtrafficquality.google',       # ← added
                'https://*.facebook.com',
                'https://graph.facebook.com',
                f"https://api.{getattr(settings, 'DOMAIN', 'feminineessencestore.com')}",
            ],

            'frame-src': [
                "'self'",
                'https://js.stripe.com',
                'https://hooks.stripe.com',
                'https://www.paypal.com',
                'https://www.youtube.com',
                'https://www.google.com',
                'https://player.vimeo.com',
                'https://td.doubleclick.net',
                'https://ad.doubleclick.net',
                'https://googleads.g.doubleclick.net',       # ← added
                'https://ep1.adtrafficquality.google',       # ← added
                'https://ep2.adtrafficquality.google',       # ← added
            ],

            'frame-ancestors': ["'self'"],

            'form-action': [
                "'self'",
                'https://checkout.stripe.com',
                'https://www.paypal.com',
            ],

            'base-uri': ["'self'"],
            'object-src': ["'none'"],

            'media-src': [
                "'self'",
                'blob:',
                f"https://{getattr(settings, 'CDN_DOMAIN', '')}",
            ],

            'worker-src': [
                "'self'",
                'blob:',
            ],

            'manifest-src': ["'self'"],
        }

        extra = getattr(request, 'csp_extra_sources', {})
        for directive, sources in extra.items():
            if directive in base_directives:
                base_directives[directive].extend(sources)
            else:
                base_directives[directive] = sources

        for directive in base_directives:
            base_directives[directive] = [
                s for s in base_directives[directive] if s and s != 'https://'
            ]

        return base_directives

    def _set_additional_headers(self, response):
        """Set supplementary security headers."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'camera=(), microphone=(), '
            'geolocation=(self), payment=(self)'
        )
        response['Cross-Origin-Opener-Policy'] = 'same-origin'