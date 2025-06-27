"""
Django admin configuration for Centers app.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Center


@admin.register(Center)
class CenterAdmin(admin.ModelAdmin):
    """
    Admin configuration for Center model.
    """
    
    list_display = [
        'name', 'schema_name', 'user_count_display', 
        'sample_count_display', 'is_active', 'created_at'
    ]
    
    list_filter = ['is_active', 'created_at', 'updated_at']
    
    search_fields = ['name', 'description', 'schema_name']
    
    readonly_fields = [
        'id', 'schema_name', 'tenant_id', 'created_at', 
        'updated_at', 'created_by', 'updated_by'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Technical Details', {
            'fields': ('schema_name', 'tenant_id', 'settings'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': (
                'id', 'created_at', 'updated_at', 
                'created_by', 'updated_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    ordering = ['name']
    
    actions = ['activate_centers', 'deactivate_centers']
    
    def user_count_display(self, obj):
        """Display user count with formatting."""
        count = obj.get_user_count()
        if count > 0:
            return format_html(
                '<strong style="color: green;">{}</strong>',
                count
            )
        return format_html(
            '<span style="color: gray;">0</span>'
        )
    user_count_display.short_description = 'Users'
    
    def sample_count_display(self, obj):
        """Display sample count with formatting."""
        try:
            count = obj.get_sample_count()
            if count > 0:
                return format_html(
                    '<strong style="color: blue;">{}</strong>',
                    count
                )
            return format_html(
                '<span style="color: gray;">0</span>'
            )
        except Exception:
            return format_html(
                '<span style="color: red;">Error</span>'
            )
    sample_count_display.short_description = 'Samples'
    
    def activate_centers(self, request, queryset):
        """Bulk action to activate centers."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} center(s) were successfully activated.'
        )
    activate_centers.short_description = "Activate selected centers"
    
    def deactivate_centers(self, request, queryset):
        """Bulk action to deactivate centers."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} center(s) were successfully deactivated.'
        )
    deactivate_centers.short_description = "Deactivate selected centers"
    
    def has_delete_permission(self, request, obj=None):
        """
        Override delete permission to prevent accidental deletion.
        Centers should be soft deleted through the API.
        """
        return False  # Prevent deletion through admin
    
    def get_queryset(self, request):
        """Override queryset to include all objects (including soft deleted)."""
        return Center.all_objects.all() 