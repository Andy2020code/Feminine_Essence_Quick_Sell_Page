from django.contrib import admin
from .models import Product, CosmeticProduct, Badge, CosmeticBadge
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import CSPViolation


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CosmeticProduct)
class CosmeticProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CosmeticBadge)
class CosmeticBadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(CSPViolation)
class CSPViolationAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp',
        'effective_directive',
        'blocked_uri_short',
        'document_uri_short',
        'ip',
        'disposition',
        'is_critical_badge',
    ]
    list_filter = [
        'effective_directive',
        'disposition',
        ('timestamp', admin.DateFieldListFilter),
    ]
    search_fields = [
        'blocked_uri',
        'document_uri',
        'ip',
        'effective_directive',
    ]
    readonly_fields = [field.name for field in CSPViolation._meta.fields]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def blocked_uri_short(self, obj):
        return obj.blocked_uri[:60] + '…' if len(obj.blocked_uri) > 60 else obj.blocked_uri
    blocked_uri_short.short_description = 'Blocked URI'

    def document_uri_short(self, obj):
        return obj.document_uri[:60] + '…' if len(obj.document_uri) > 60 else obj.document_uri
    document_uri_short.short_description = 'Page'

    def is_critical_badge(self, obj):
        if obj.is_critical:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Critical</span>')
        return format_html('<span style="color:green;">✓ Normal</span>')
    is_critical_badge.short_description = 'Severity'

    def changelist_view(self, request, extra_context=None):
        """Add summary stats to the changelist page."""
        extra_context = extra_context or {}

        last_24h = timezone.now() - timedelta(hours=24)
        recent = CSPViolation.objects.filter(timestamp__gte=last_24h)

        extra_context['summary'] = {
            'total_24h': recent.count(),
            'critical_24h': recent.filter(
                effective_directive__in=[
                    'script-src', 'frame-ancestors', 'form-action'
                ]
            ).count(),
            'top_directives': list(
                recent.values('effective_directive')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            ),
        }

        return super().changelist_view(request, extra_context=extra_context)