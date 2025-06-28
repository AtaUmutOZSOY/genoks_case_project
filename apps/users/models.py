"""
User model for multi-tenant application.
Users are stored in the public schema and can be associated with centers.
"""

from django.db import models
from django.core.validators import EmailValidator
from apps.common.models import BaseModel
from apps.centers.models import Center


class User(BaseModel):
    """
    User model for the multi-tenant system.
    Users are stored in the public schema and can access one or more centers.
    """
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('user', 'User'),
        ('viewer', 'Viewer'),
    ]
    
    username = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique username for the user"
    )
    
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="User's email address"
    )
    
    first_name = models.CharField(
        max_length=50,
        help_text="User's first name"
    )
    
    last_name = models.CharField(
        max_length=50,
        help_text="User's last name"
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="User's phone number (optional)"
    )
    
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='users',
        help_text="Center this user belongs to"
    )
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
        help_text="User's role in the system"
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['first_name', 'last_name']
        
        # Ensure unique username and email
        constraints = [
            models.UniqueConstraint(
                fields=['username'],
                name='unique_username'
            ),
            models.UniqueConstraint(
                fields=['email'],
                name='unique_email'
            ),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"
    
    def clean(self):
        """Validate the model fields."""
        super().clean()
        
        # Normalize email to lowercase
        if self.email:
            self.email = self.email.lower().strip()
        
        # Normalize username to lowercase
        if self.username:
            self.username = self.username.lower().strip()
        
        # Ensure center is active
        if self.center and not self.center.is_active:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'center': 'Cannot assign user to an inactive center.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and normalization."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the user's first name."""
        return self.first_name
    
    @property
    def full_name(self):
        """Property to get full name."""
        return self.get_full_name()
    
    @property
    def is_admin(self):
        """Check if user is an administrator."""
        return self.role == 'admin'
    
    @property
    def is_viewer(self):
        """Check if user is a viewer (read-only)."""
        return self.role == 'viewer'
    
    @property
    def center_name(self):
        """Get the name of the user's center."""
        return self.center.name if self.center else None
    
    @property
    def center_schema(self):
        """Get the schema name of the user's center."""
        return self.center.schema_name if self.center else None
    
    @property
    def is_authenticated(self):
        """Check if user is authenticated (always True for saved users)."""
        return True
    
    @property
    def is_anonymous(self):
        """Check if user is anonymous (always False for saved users)."""
        return False
    
    def can_access_center(self, center):
        """
        Check if user can access a specific center.
        Currently, users can only access their assigned center.
        This can be extended for multi-center access.
        """
        return self.center == center and center.is_active
    
    def get_sample_count(self):
        """
        Get the number of samples created by this user.
        This requires switching to the tenant schema.
        """
        try:
            from utils.tenant_utils import set_tenant_schema_context
            from apps.samples.models import Sample
            
            with set_tenant_schema_context(self.center.tenant_id):
                # Assuming samples have a user_id field that references this user
                return Sample.objects.filter(user_id=self.id).count()
        except Exception:
            return 0
    
    def change_center(self, new_center, user=None):
        """
        Change the user's center assignment.
        
        Args:
            new_center: New center to assign user to
            user: User performing the change (for audit)
        """
        if not new_center.is_active:
            raise ValueError("Cannot assign user to an inactive center")
        
        old_center = self.center
        self.center = new_center
        if user:
            self.updated_by = str(user)
        
        self.save()
        
        return {
            'old_center': old_center.name if old_center else None,
            'new_center': new_center.name,
            'changed_by': str(user) if user else None
        }
    
    def update_role(self, new_role, user=None):
        """
        Update the user's role.
        
        Args:
            new_role: New role to assign
            user: User performing the change (for audit)
        """
        if new_role not in dict(self.ROLE_CHOICES):
            raise ValueError(f"Invalid role: {new_role}")
        
        old_role = self.role
        self.role = new_role
        if user:
            self.updated_by = str(user)
        
        self.save()
        
        return {
            'old_role': old_role,
            'new_role': new_role,
            'changed_by': str(user) if user else None
        }
    
    @classmethod
    def get_users_by_center(cls, center):
        """
        Get all active users for a specific center.
        
        Args:
            center: Center instance
            
        Returns:
            QuerySet of users
        """
        return cls.objects.filter(center=center, is_active=True)
    
    @classmethod
    def get_admins_by_center(cls, center):
        """
        Get all admin users for a specific center.
        
        Args:
            center: Center instance
            
        Returns:
            QuerySet of admin users
        """
        return cls.objects.filter(
            center=center,
            role='admin',
            is_active=True
        ) 