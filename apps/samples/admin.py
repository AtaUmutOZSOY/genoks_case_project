"""
Admin configuration for the samples app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Sample


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    """
    Custom admin for Sample model.
    """
    list_display = [
        'name', 'sample_type', 'status_display', 'barcode',
        'user_name_display', 'collection_date', 'days_since_collection_display',
        'is_active', 'created_at'
    ]
    list_filter = [
        'sample_type', 'status', 'is_active', 'collection_date',
        'created_at', 'processing_started', 'processing_completed'
    ]
    search_fields = ['name', 'description', 'barcode', 'collection_location']
    ordering = ['-created_at']
    readonly_fields = [
        'id', 'barcode', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'processing_started', 'processing_completed', 'user_name_display'
    ]
    
    # Custom fieldsets
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'sample_type', 'user_id')
        }),
        (_('Status & Processing'), {
            'fields': ('status', 'processing_started', 'processing_completed')
        }),
        (_('Collection Details'), {
            'fields': ('collection_date', 'collection_location', 'barcode'),
            'classes': ('collapse',)
        }),
        (_('Data'), {
            'fields': ('metadata', 'results'),
            'classes': ('collapse',)
        }),
        (_('System Fields'), {
            'fields': ('is_active', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'rejected': 'red',
            'archived': 'gray'
        }
        
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def user_name_display(self, obj):
        """Display user name."""
        return obj.user_name
    user_name_display.short_description = 'User'
    
    def days_since_collection_display(self, obj):
        """Display days since collection."""
        days = obj.days_since_collection
        if days is not None:
            if days > 30:
                color = 'red'
            elif days > 7:
                color = 'orange'
            else:
                color = 'green'
            
            return format_html(
                '<span style="color: {};">{} days</span>',
                color,
                days
            )
        return '-'
    days_since_collection_display.short_description = 'Days Since Collection'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs
    
    actions = ['start_processing', 'complete_processing', 'reject_samples', 'archive_samples']
    
    def start_processing(self, request, queryset):
        """Bulk start processing for pending samples."""
        count = 0
        for sample in queryset.filter(status='pending'):
            try:
                sample.start_processing(user=request.user)
                count += 1
            except ValueError:
                pass  # Skip samples that can't be processed
        
        self.message_user(
            request,
            f'Successfully started processing for {count} sample(s).'
        )
    start_processing.short_description = 'Start processing for selected samples'
    
    def complete_processing(self, request, queryset):
        """Bulk complete processing for processing samples."""
        count = 0
        for sample in queryset.filter(status='processing'):
            try:
                sample.complete_processing(user=request.user)
                count += 1
            except ValueError:
                pass  # Skip samples that can't be completed
        
        self.message_user(
            request,
            f'Successfully completed processing for {count} sample(s).'
        )
    complete_processing.short_description = 'Complete processing for selected samples'
    
    def reject_samples(self, request, queryset):
        """Bulk reject samples."""
        count = 0
        for sample in queryset.exclude(status__in=['archived']):
            try:
                sample.reject_sample(reason='Bulk rejection from admin', user=request.user)
                count += 1
            except ValueError:
                pass  # Skip samples that can't be rejected
        
        self.message_user(
            request,
            f'Successfully rejected {count} sample(s).'
        )
    reject_samples.short_description = 'Reject selected samples'
    
    def archive_samples(self, request, queryset):
        """Bulk archive samples."""
        count = 0
        for sample in queryset.filter(status__in=['completed', 'rejected']):
            try:
                sample.archive_sample(user=request.user)
                count += 1
            except ValueError:
                pass  # Skip samples that can't be archived
        
        self.message_user(
            request,
            f'Successfully archived {count} sample(s).'
        )
    archive_samples.short_description = 'Archive selected samples'
    
    def has_delete_permission(self, request, obj=None):
        """
        Override delete permission to prevent accidental deletion.
        Samples should be soft deleted through the API.
        """
        return False  # Prevent deletion through admin 