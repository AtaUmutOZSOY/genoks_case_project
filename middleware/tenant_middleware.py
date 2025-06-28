"""
Multi-tenant middleware for schema-based tenant isolation.
"""

import re
from django.db import connection
from django.http import Http404
from django.conf import settings
from django.core.cache import cache


class TenantMiddleware:
    """
    Middleware that handles tenant schema switching based on URL patterns.
    
    For tenant-specific URLs like /api/centers/{center_id}/samples/,
    this middleware will:
    1. Extract the center_id from the URL
    2. Set the database schema to center_{center_id}
    3. Store tenant context for use in views
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Compile regex patterns for better performance - support UUID format
        self.tenant_url_pattern = re.compile(r'/api/centers/([a-f0-9-]{36})/')
        
    def __call__(self, request):
        # Extract tenant info from URL
        tenant_info = self.extract_tenant_info(request)
        
        if tenant_info:
            # Set tenant context
            request.tenant = tenant_info
            
            # Set database schema
            self.set_tenant_schema(tenant_info['center_id'])
        else:
            # For non-tenant URLs, use public schema
            request.tenant = None
            self.set_public_schema()
        
        response = self.get_response(request)
        
        # Reset to public schema after request
        self.set_public_schema()
        
        return response
    
    def extract_tenant_info(self, request):
        """
        Extract tenant information from the request URL.
        
        Args:
            request: Django request object
            
        Returns:
            dict: Tenant information if found, None otherwise
        """
        path = request.path
        
        # Check if this is a tenant-specific URL
        match = self.tenant_url_pattern.search(path)
        if match:
            center_id = match.group(1)  # UUID string, not int
            
            # Validate that the center exists (with caching)
            if self.validate_center_exists(center_id):
                return {
                    'center_id': center_id,
                    'schema_name': f"{settings.TENANT_SCHEMA_PREFIX}{center_id.replace('-', '')}"
                }
            else:
                raise Http404(f"Center with ID {center_id} does not exist")
        
        return None
    
    def validate_center_exists(self, center_id):
        """
        Validate that a center exists.
        Uses caching to avoid frequent database queries.
        
        Args:
            center_id: ID of the center to validate (UUID string)
            
        Returns:
            bool: True if center exists, False otherwise
        """
        cache_key = f"center_exists_{center_id}"
        exists = cache.get(cache_key)
        
        if exists is None:
            # Import here to avoid circular imports
            from apps.centers.models import Center
            
            try:
                # Use public schema to check center existence
                self.set_public_schema()
                exists = Center.objects.filter(id=center_id, is_active=True).exists()
                # Cache for 5 minutes
                cache.set(cache_key, exists, 300)
            except Exception:
                exists = False
        
        return exists
    
    def set_tenant_schema(self, center_id):
        """
        Set the database schema to the tenant schema.
        
        Args:
            center_id: ID of the center/tenant (UUID string)
        """
        # Remove hyphens from UUID for schema name
        schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id.replace('-', '')}"
        self.set_schema(schema_name)
    
    def set_public_schema(self):
        """Set the database schema to the public schema."""
        self.set_schema(settings.PUBLIC_SCHEMA_NAME)
    
    def set_schema(self, schema_name):
        """
        Set the PostgreSQL search_path to the specified schema.
        
        Args:
            schema_name: Name of the schema to switch to
        """
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {schema_name}, public")
    
    def process_exception(self, request, exception):
        """
        Handle exceptions by resetting to public schema.
        
        Args:
            request: Django request object
            exception: Exception that occurred
        """
        # Always reset to public schema on exception
        try:
            self.set_public_schema()
        except Exception:
            # If we can't reset schema, there's a bigger problem
            pass
        
        # Let Django handle the exception normally
        return None


class TenantContextMiddleware:
    """
    Lightweight middleware that only adds tenant context without schema switching.
    Useful for views that need tenant info but don't need schema switching.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.tenant_url_pattern = re.compile(r'/api/centers/([a-f0-9-]{36})/')
    
    def __call__(self, request):
        # Extract tenant info from URL
        match = self.tenant_url_pattern.search(request.path)
        if match:
            center_id = match.group(1)  # UUID string
            request.tenant = {
                'center_id': center_id,
                'schema_name': f"{settings.TENANT_SCHEMA_PREFIX}{center_id.replace('-', '')}"
            }
        else:
            request.tenant = None
        
        response = self.get_response(request)
        return response 