"""
Utility functions for tenant management and schema operations.
"""

from django.db import connection, transaction
from django.conf import settings
from django.core.management import call_command
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def create_tenant_schema(center_id):
    """
    Create a new tenant schema for a center.
    
    Args:
        center_id: ID of the center
        
    Returns:
        bool: True if schema was created successfully, False otherwise
    """
    schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id}"
    
    try:
        with connection.cursor() as cursor:
            # Create the schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            
            # Grant necessary permissions
            cursor.execute(f"GRANT USAGE ON SCHEMA {schema_name} TO public")
            cursor.execute(f"GRANT CREATE ON SCHEMA {schema_name} TO public")
            
        # Run migrations for the new schema
        migrate_tenant_schema(center_id)
        
        # Clear cache
        cache.delete(f"center_exists_{center_id}")
        
        logger.info(f"Successfully created tenant schema: {schema_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create tenant schema {schema_name}: {str(e)}")
        return False


def delete_tenant_schema(center_id):
    """
    Delete a tenant schema and all its data.
    
    Args:
        center_id: ID of the center
        
    Returns:
        bool: True if schema was deleted successfully, False otherwise
    """
    schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id}"
    
    try:
        with connection.cursor() as cursor:
            # Drop the schema and all its objects
            cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        
        # Clear cache
        cache.delete(f"center_exists_{center_id}")
        
        logger.info(f"Successfully deleted tenant schema: {schema_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete tenant schema {schema_name}: {str(e)}")
        return False


def migrate_tenant_schema(center_id):
    """
    Run Django migrations for a specific tenant schema.
    
    Args:
        center_id: ID of the center
        
    Returns:
        bool: True if migrations ran successfully, False otherwise
    """
    schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id}"
    
    try:
        # Set search path to tenant schema
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {schema_name}, public")
        
        # Run migrations for tenant-specific apps
        tenant_apps = ['samples']  # Apps that should be in tenant schema
        
        for app in tenant_apps:
            call_command('migrate', app_label=app, verbosity=0, interactive=False)
        
        logger.info(f"Successfully migrated tenant schema: {schema_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to migrate tenant schema {schema_name}: {str(e)}")
        return False
    finally:
        # Reset to public schema
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO public")


def list_tenant_schemas():
    """
    List all tenant schemas in the database.
    
    Returns:
        list: List of tenant schema names
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE %s
            """, [f"{settings.TENANT_SCHEMA_PREFIX}%"])
            
            return [row[0] for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Failed to list tenant schemas: {str(e)}")
        return []


def get_tenant_id_from_schema(schema_name):
    """
    Extract tenant ID from schema name.
    
    Args:
        schema_name: Name of the schema
        
    Returns:
        int: Tenant ID or None if invalid schema name
    """
    if schema_name.startswith(settings.TENANT_SCHEMA_PREFIX):
        try:
            return int(schema_name[len(settings.TENANT_SCHEMA_PREFIX):])
        except ValueError:
            return None
    return None


def schema_exists(center_id):
    """
    Check if a tenant schema exists.
    
    Args:
        center_id: ID of the center
        
    Returns:
        bool: True if schema exists, False otherwise
    """
    schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id}"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 
                FROM information_schema.schemata 
                WHERE schema_name = %s
            """, [schema_name])
            
            return cursor.fetchone() is not None
            
    except Exception as e:
        logger.error(f"Failed to check schema existence {schema_name}: {str(e)}")
        return False


def set_tenant_schema_context(center_id):
    """
    Context manager for temporarily switching to a tenant schema.
    
    Args:
        center_id: ID of the center
        
    Usage:
        with set_tenant_schema_context(1):
            # Database operations here will use center_1 schema
            Sample.objects.all()
    """
    return TenantSchemaContext(center_id)


class TenantSchemaContext:
    """
    Context manager for tenant schema switching.
    """
    
    def __init__(self, center_id):
        self.center_id = center_id
        self.schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{center_id}"
        self.original_schema = None
    
    def __enter__(self):
        # Store current schema
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            self.original_schema = cursor.fetchone()[0]
            
            # Set to tenant schema
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original schema
        with connection.cursor() as cursor:
            if self.original_schema:
                cursor.execute(f"SET search_path TO {self.original_schema}")
            else:
                cursor.execute("SET search_path TO public")


def migrate_all_tenant_schemas():
    """
    Run migrations for all existing tenant schemas.
    
    Returns:
        dict: Results of migration for each schema
    """
    results = {}
    tenant_schemas = list_tenant_schemas()
    
    for schema_name in tenant_schemas:
        center_id = get_tenant_id_from_schema(schema_name)
        if center_id:
            results[schema_name] = migrate_tenant_schema(center_id)
        else:
            results[schema_name] = False
            logger.warning(f"Could not extract center ID from schema: {schema_name}")
    
    return results 