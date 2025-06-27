"""
Center model for multi-tenant application.
Centers are stored in the public schema and represent tenants.
"""

from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel
from utils.tenant_utils import create_tenant_schema, delete_tenant_schema
import re


class Center(BaseModel):
    """
    Center model representing a tenant in the multi-tenant system.
    Each center gets its own database schema for data isolation.
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the center (must be unique)"
    )
    
    schema_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Database schema name for this center"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the center"
    )
    
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Center-specific configuration settings"
    )
    
    class Meta:
        db_table = 'centers'
        verbose_name = 'Center'
        verbose_name_plural = 'Centers'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.schema_name})"
    
    def clean(self):
        """Validate the model fields."""
        super().clean()
        
        # Validate schema name format
        if self.schema_name:
            if not re.match(r'^[a-z][a-z0-9_]*$', self.schema_name):
                raise ValidationError({
                    'schema_name': 'Schema name must start with a letter and contain only lowercase letters, numbers, and underscores.'
                })
            
            # Ensure schema name starts with the tenant prefix
            from django.conf import settings
            if not self.schema_name.startswith(settings.TENANT_SCHEMA_PREFIX):
                self.schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{self.schema_name}"
    
    def save(self, *args, **kwargs):
        """Override save to handle schema creation."""
        is_new = self.pk is None
        
        # Generate schema name if not provided
        if not self.schema_name:
            from django.conf import settings
            # Use the center ID (will be available after save)
            if is_new:
                # For new centers, we'll generate schema name after getting the ID
                super().save(*args, **kwargs)
                self.schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{self.pk}"
                super().save(update_fields=['schema_name'])
            else:
                self.schema_name = f"{settings.TENANT_SCHEMA_PREFIX}{self.pk}"
        
        if not is_new:
            super().save(*args, **kwargs)
        elif self.schema_name:
            super().save(*args, **kwargs)
        
        # Create tenant schema for new centers
        if is_new and self.schema_name:
            center_id = str(self.pk).replace('-', '')  # Remove hyphens from UUID
            success = create_tenant_schema(center_id)
            if not success:
                # If schema creation fails, we should handle this appropriately
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create schema for center {self.name}")
    
    def delete(self, *args, **kwargs):
        """Override delete to handle schema deletion."""
        center_id = str(self.pk).replace('-', '')  # Remove hyphens from UUID
        
        # Perform soft delete first
        self.soft_delete()
        
        # Optionally delete the schema (be careful with this!)
        # delete_tenant_schema(center_id)
    
    def hard_delete(self):
        """Permanently delete the center and its schema."""
        center_id = str(self.pk).replace('-', '')  # Remove hyphens from UUID
        
        # Delete the tenant schema
        delete_tenant_schema(center_id)
        
        # Delete the center record
        super().delete()
    
    @property
    def full_schema_name(self):
        """Get the full schema name including prefix."""
        return self.schema_name
    
    @property
    def tenant_id(self):
        """Get the tenant ID (used for schema operations)."""
        return str(self.pk).replace('-', '')
    
    def get_setting(self, key, default=None):
        """
        Get a specific setting value.
        
        Args:
            key: Setting key
            default: Default value if key doesn't exist
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """
        Set a specific setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        if not isinstance(self.settings, dict):
            self.settings = {}
        self.settings[key] = value
        self.save(update_fields=['settings'])
    
    def get_sample_count(self):
        """
        Get the total number of samples in this center.
        This requires switching to the tenant schema.
        """
        try:
            from utils.tenant_utils import set_tenant_schema_context
            from apps.samples.models import Sample
            
            with set_tenant_schema_context(self.tenant_id):
                return Sample.objects.count()
        except Exception:
            return 0
    
    def get_user_count(self):
        """Get the number of users in this center."""
        return self.users.filter(is_active=True).count()
    
    @classmethod
    def get_by_schema_name(cls, schema_name):
        """
        Get a center by its schema name.
        
        Args:
            schema_name: Schema name to search for
            
        Returns:
            Center instance or None
        """
        try:
            return cls.objects.get(schema_name=schema_name, is_active=True)
        except cls.DoesNotExist:
            return None 