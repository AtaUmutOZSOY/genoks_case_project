"""
Sample model for multi-tenant application.
Samples are stored in tenant-specific schemas.
"""

from django.db import models
from django.core.exceptions import ValidationError
from apps.common.models import BaseModel
import uuid


class Sample(BaseModel):
    """
    Sample model representing tenant-specific sample data.
    Each sample is stored in its center's dedicated schema.
    """
    
    SAMPLE_TYPE_CHOICES = [
        ('blood', 'Blood'),
        ('urine', 'Urine'),
        ('tissue', 'Tissue'),
        ('saliva', 'Saliva'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Name or identifier of the sample"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the sample"
    )
    
    sample_type = models.CharField(
        max_length=20,
        choices=SAMPLE_TYPE_CHOICES,
        default='other',
        help_text="Type of the sample"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the sample"
    )
    
    barcode = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="Unique barcode identifier for the sample"
    )
    
    user_id = models.UUIDField(
        help_text="ID of the user who created this sample (references public.users)"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata for the sample"
    )
    
    # Collection information
    collection_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when the sample was collected"
    )
    
    collection_location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Location where the sample was collected"
    )
    
    # Processing information
    processing_started = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when processing started"
    )
    
    processing_completed = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date when processing was completed"
    )
    
    # Results
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sample processing results"
    )
    
    class Meta:
        db_table = 'samples'
        verbose_name = 'Sample'
        verbose_name_plural = 'Samples'
        ordering = ['-created_at']
        
        # Ensure unique barcode within tenant
        constraints = [
            models.UniqueConstraint(
                fields=['barcode'],
                condition=models.Q(barcode__isnull=False),
                name='unique_barcode_per_tenant'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sample_type}) - {self.status}"
    
    def clean(self):
        """Validate the model fields."""
        super().clean()
        
        # Validate barcode format if provided
        if self.barcode:
            self.barcode = self.barcode.upper().strip()
            if len(self.barcode) < 3:
                raise ValidationError({
                    'barcode': 'Barcode must be at least 3 characters long.'
                })
        
        # Validate metadata
        if self.metadata and not isinstance(self.metadata, dict):
            raise ValidationError({
                'metadata': 'Metadata must be a valid JSON object.'
            })
        
        # Validate results
        if self.results and not isinstance(self.results, dict):
            raise ValidationError({
                'results': 'Results must be a valid JSON object.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to perform validation and generate barcode."""
        # Generate barcode if not provided
        if not self.barcode:
            self.barcode = self.generate_barcode()
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def generate_barcode(self):
        """Generate a unique barcode for the sample."""
        import datetime
        import random
        
        # Format: YYYYMMDD-XXXX (where XXXX is random)
        date_part = datetime.datetime.now().strftime('%Y%m%d')
        random_part = f"{random.randint(1000, 9999)}"
        
        barcode = f"{date_part}-{random_part}"
        
        # Ensure uniqueness within tenant
        counter = 1
        original_barcode = barcode
        while Sample.objects.filter(barcode=barcode).exists():
            barcode = f"{original_barcode}-{counter:02d}"
            counter += 1
        
        return barcode
    
    @property
    def user_name(self):
        """Get the name of the user who created this sample."""
        try:
            # Import here to avoid circular imports
            from apps.users.models import User
            user = User.objects.get(id=self.user_id)
            return user.get_full_name()
        except User.DoesNotExist:
            return "Unknown User"
    
    @property
    def is_processing(self):
        """Check if sample is currently being processed."""
        return self.status == 'processing'
    
    @property
    def is_completed(self):
        """Check if sample processing is completed."""
        return self.status == 'completed'
    
    @property
    def days_since_collection(self):
        """Get number of days since collection."""
        if self.collection_date:
            from django.utils import timezone
            return (timezone.now() - self.collection_date).days
        return None
    
    def start_processing(self, user=None):
        """Mark sample as processing."""
        from django.utils import timezone
        
        if self.status != 'pending':
            raise ValueError(f"Cannot start processing sample with status: {self.status}")
        
        self.status = 'processing'
        self.processing_started = timezone.now()
        if user:
            self.updated_by = str(user)
        
        self.save()
    
    def complete_processing(self, results=None, user=None):
        """Mark sample as completed with optional results."""
        from django.utils import timezone
        
        if self.status != 'processing':
            raise ValueError(f"Cannot complete sample with status: {self.status}")
        
        self.status = 'completed'
        self.processing_completed = timezone.now()
        
        if results:
            if isinstance(results, dict):
                self.results = results
            else:
                raise ValueError("Results must be a dictionary")
        
        if user:
            self.updated_by = str(user)
        
        self.save()
    
    def reject_sample(self, reason=None, user=None):
        """Reject the sample with optional reason."""
        self.status = 'rejected'
        
        if reason:
            if not self.metadata:
                self.metadata = {}
            self.metadata['rejection_reason'] = reason
        
        if user:
            self.updated_by = str(user)
        
        self.save()
    
    def archive_sample(self, user=None):
        """Archive the sample."""
        if self.status not in ['completed', 'rejected']:
            raise ValueError(f"Cannot archive sample with status: {self.status}")
        
        self.status = 'archived'
        if user:
            self.updated_by = str(user)
        
        self.save()
    
    def get_metadata_value(self, key, default=None):
        """Get a specific metadata value."""
        return self.metadata.get(key, default) if self.metadata else default
    
    def set_metadata_value(self, key, value):
        """Set a specific metadata value."""
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata[key] = value
        self.save(update_fields=['metadata'])
    
    @classmethod
    def get_by_barcode(cls, barcode):
        """Get sample by barcode."""
        try:
            return cls.objects.get(barcode=barcode.upper().strip())
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_samples_by_user(cls, user_id):
        """Get all samples created by a specific user."""
        return cls.objects.filter(user_id=user_id)
    
    @classmethod
    def get_samples_by_status(cls, status):
        """Get all samples with a specific status."""
        return cls.objects.filter(status=status)
    
    @classmethod
    def get_samples_by_type(cls, sample_type):
        """Get all samples of a specific type."""
        return cls.objects.filter(sample_type=sample_type) 