"""
Admin configuration for the users app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Custom admin for User model.
    """
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'center_link', 'role', 'is_active', 'created_at'
    ]
    list_filter = ['role', 'center', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('Center & Role', {
            'fields': ('center', 'role')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('id', 'created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def center_link(self, obj):
        if obj.center:
            url = reverse('admin:centers_center_change', args=[obj.center.pk])
            return format_html('<a href="{}">{}</a>', url, obj.center.name)
        return '-'
    center_link.short_description = 'Center'
    center_link.admin_order_field = 'center__name'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('username',)
        return self.readonly_fields

    actions = ['activate_users', 'deactivate_users', 'assign_admin_role', 'assign_user_role']

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users were successfully activated.')
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users were successfully deactivated.')
    deactivate_users.short_description = "Deactivate selected users"

    def assign_admin_role(self, request, queryset):
        updated = queryset.update(role='admin')
        self.message_user(request, f'{updated} users were assigned admin role.')
    assign_admin_role.short_description = "Assign admin role"

    def assign_user_role(self, request, queryset):
        updated = queryset.update(role='user')
        self.message_user(request, f'{updated} users were assigned user role.')
    assign_user_role.short_description = "Assign user role"


# Customize admin site
admin.site.site_header = 'Multi-tenant System Administration'
admin.site.site_title = 'Multi-tenant Admin'
admin.site.index_title = 'Welcome to Multi-tenant Administration' 