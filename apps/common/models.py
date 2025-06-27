"""
Common models and base functionality for multi-tenant application.
"""

import uuid
from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    """Manager that returns only active (non-soft-deleted) records."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class AllObjectsManager(models.Manager):
    """Manager that returns all records including soft-deleted ones."""
    
    def get_queryset(self):
        return super().get_queryset()


class BaseModel(models.Model):
    """
    Abstract base model that provides common fields for all models:
    - UUID primary key
    - Timestamps (created_at, updated_at)
    - Soft delete functionality (is_active)
    - Audit trail (created_by, updated_by)
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this record is active (used for soft delete)"
    )
    
    created_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Username of the user who created this record"
    )
    
    updated_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Username of the user who last updated this record"
    )
    
    # Managers
    objects = ActiveManager()  # Default manager (only active records)
    all_objects = AllObjectsManager()  # All records including soft deleted
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def soft_delete(self, user=None):
        """
        Soft delete this record by setting is_active to False.
        
        Args:
            user: User performing the soft delete (optional)
        """
        self.is_active = False
        if user:
            self.updated_by = str(user)
        self.updated_at = timezone.now()
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def restore(self, user=None):
        """
        Restore a soft-deleted record by setting is_active to True.
        
        Args:
            user: User performing the restore (optional)
        """
        self.is_active = True
        if user:
            self.updated_by = str(user)
        self.updated_at = timezone.now()
        self.save(update_fields=['is_active', 'updated_by', 'updated_at'])
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps and audit fields."""
        # Set updated_at manually since auto_now doesn't work with update_fields
        if 'update_fields' in kwargs and 'updated_at' not in kwargs['update_fields']:
            kwargs['update_fields'].append('updated_at')
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        """String representation showing the ID and creation time."""
        return f"{self.__class__.__name__} {str(self.id)[:8]} (created: {self.created_at})" 