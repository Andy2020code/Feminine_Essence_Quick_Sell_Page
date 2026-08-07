# apps/core/views/csp_report.py

import json
import logging
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import SuspiciousOperation

logger = logging.getLogger('csp.violations')
critical_logger = logging.getLogger('csp.critical')


@method_decorator(csrf_exempt, name='dispatch')
class CSPReportView(View):
    """
    Endpoint to receive and log CSP violation reports.
    Route: POST /csp-report/
    """

    # Allowed content types for CSP reports
    VALID_CONTENT_TYPES = (
        'application/csp-report',
        'application/json',
    )

    # Directives that indicate a possible attack
    CRITICAL_DIRECTIVES = {
        'script-src',
        'script-src-elem',
        'frame-ancestors',
        'form-action',
        'object-src',
    }

    # Simple in-memory rate limiting (use Redis/cache in production)
    _rate_limit_cache = {}
    RATE_LIMIT = 50          # max reports per window
    RATE_WINDOW = 3600       # 1 hour in seconds

    def post(self, request, *args, **kwargs):
        # Validate content type
        content_type = request.content_type or ''
        if not any(ct in content_type for ct in self.VALID_CONTENT_TYPES):
            return HttpResponse(status=400)

        # Rate limiting
        if not self._check_rate_limit(request):
            return HttpResponse(status=429)

        # Parse body
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HttpResponse(status=400)

        # Extract violation (handle both CSP Level 2 and Level 3 formats)
        violation = body.get('csp-report') or body
        if not violation:
            return HttpResponse(status=400)

        # Build structured log entry
        log_entry = self._build_log_entry(request, violation)

        # Log the violation
        self._log_violation(log_entry)

        # Save to database
        self._save_to_db(log_entry)

        return HttpResponse(status=204)

    def _build_log_entry(self, request, violation: dict) -> dict:
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            'document_uri': violation.get('document-uri', '')[:2000],
            'referrer': violation.get('referrer', '')[:2000],
            'violated_directive': violation.get('violated-directive', '')[:255],
            'effective_directive': violation.get('effective-directive', '')[:255],
            'original_policy': violation.get('original-policy', '')[:5000],
            'blocked_uri': violation.get('blocked-uri', '')[:2000],
            'source_file': violation.get('source-file', '')[:2000],
            'line_number': violation.get('line-number', 0),
            'column_number': violation.get('column-number', 0),
            'status_code': violation.get('status-code', 0),
            'script_sample': violation.get('script-sample', '')[:512],
            'disposition': violation.get('disposition', 'enforce'),
        }

    def _log_violation(self, entry: dict) -> None:
        effective = entry.get('effective_directive', '')
        blocked = entry.get('blocked_uri', '')
        doc = entry.get('document_uri', '')

        msg = (
            f"CSP Violation | directive={effective} | "
            f"blocked={blocked} | document={doc} | "
            f"ip={entry['ip']}"
        )

        if effective in self.CRITICAL_DIRECTIVES:
            critical_logger.critical(msg, extra={'csp_report': entry})
        else:
            logger.warning(msg, extra={'csp_report': entry})

    def _save_to_db(self, entry: dict) -> None:
        """Save violation to database if model exists."""
        try:
            from core.models import CSPViolation
            CSPViolation.objects.create(**entry)
        except Exception as exc:
            logger.error(f'Failed to save CSP violation to DB: {exc}')

    def _get_client_ip(self, request) -> str:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _check_rate_limit(self, request) -> bool:
        """Basic rate limiting. Replace with Django cache / Redis in production."""
        from django.core.cache import cache

        ip = self._get_client_ip(request)
        cache_key = f'csp_rl_{ip}'
        count = cache.get(cache_key, 0)

        if count >= self.RATE_LIMIT:
            return False

        cache.set(cache_key, count + 1, timeout=self.RATE_WINDOW)
        return True