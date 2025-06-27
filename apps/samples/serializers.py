"""
Serializers for Sample model.
"""

from rest_framework import serializers
from apps.common.serializers import BaseModelSerializer
from .models import Sample


class SampleSerializer(BaseModelSerializer):
    """
    Serializer for Sample model with full details.
    """
    
    # Add computed fields
    user_name = serializers.ReadOnlyField()
    is_processing = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    days_since_collection = serializers.ReadOnlyField()
    
    # Format datetime fields
    collection_date = serializers.DateTimeField(allow_null=True, required=False)
    processing_started = serializers.DateTimeField(read_only=True)
    processing_completed = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Sample
        fields = BaseModelSerializer.Meta.fields + [
            'name', 'description', 'sample_type', 'status', 'barcode',
            'user_id', 'metadata', 'collection_date', 'collection_location',
            'processing_started', 'processing_completed', 'results',
            'user_name', 'is_processing', 'is_completed', 'days_since_collection'
        ]
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + [
            'barcode', 'processing_started', 'processing_completed',
            'user_name', 'is_processing', 'is_completed', 'days_since_collection'
        ]
    
    def validate_sample_type(self, value):
        """Validate sample type."""
        valid_types = [choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid sample type. Must be one of: {', '.join(valid_types)}"
            )
        return value
    
    def validate_status(self, value):
        """Validate status."""
        valid_statuses = [choice[0] for choice in Sample.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value
    
    def validate_name(self, value):
        """Validate sample name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Sample name must be at least 2 characters long.")
        return value.strip()
    
    def validate_user_id(self, value):
        """Validate user ID."""
        if not value:
            raise serializers.ValidationError("User ID is required.")
        
        # Check if user exists in public schema
        try:
            from apps.users.models import User
            User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found or inactive.")
        
        return value
    
    def validate_metadata(self, value):
        """Validate metadata JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a valid JSON object.")
        
        return value
    
    def validate_results(self, value):
        """Validate results JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Results must be a valid JSON object.")
        
        return value


class SampleListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for Sample list views.
    """
    
    user_name = serializers.ReadOnlyField()
    days_since_collection = serializers.ReadOnlyField()
    
    class Meta:
        model = Sample
        fields = [
            'id', 'name', 'sample_type', 'status', 'barcode',
            'user_name', 'collection_date', 'days_since_collection',
            'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'barcode', 'user_name', 'days_since_collection', 'created_at']


class SampleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new samples.
    """
    
    class Meta:
        model = Sample
        fields = [
            'name', 'description', 'sample_type', 'user_id',
            'metadata', 'collection_date', 'collection_location'
        ]
    
    def validate_name(self, value):
        """Validate sample name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Sample name must be at least 2 characters long.")
        return value.strip()
    
    def validate_user_id(self, value):
        """Validate user ID."""
        if not value:
            raise serializers.ValidationError("User ID is required.")
        
        # Check if user exists in public schema
        try:
            from apps.users.models import User
            User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found or inactive.")
        
        return value
    
    def validate_sample_type(self, value):
        """Validate sample type."""
        valid_types = [choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid sample type. Must be one of: {', '.join(valid_types)}"
            )
        return value
    
    def validate_metadata(self, value):
        """Validate metadata JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a valid JSON object.")
        
        return value
    
    def create(self, validated_data):
        """Create sample with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = str(request.user.username)
            validated_data['updated_by'] = str(request.user.username)
        
        return Sample.objects.create(**validated_data)


class SampleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating samples.
    """
    
    class Meta:
        model = Sample
        fields = [
            'name', 'description', 'sample_type', 'status',
            'metadata', 'collection_date', 'collection_location',
            'results', 'is_active'
        ]
    
    def validate_name(self, value):
        """Validate sample name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Sample name must be at least 2 characters long.")
        return value.strip()
    
    def validate_sample_type(self, value):
        """Validate sample type."""
        valid_types = [choice[0] for choice in Sample.SAMPLE_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid sample type. Must be one of: {', '.join(valid_types)}"
            )
        return value
    
    def validate_status(self, value):
        """Validate status transitions."""
        instance = self.instance
        if instance:
            # Define valid status transitions
            valid_transitions = {
                'pending': ['processing', 'rejected'],
                'processing': ['completed', 'rejected'],
                'completed': ['archived'],
                'rejected': ['archived'],
                'archived': []  # No transitions from archived
            }
            
            current_status = instance.status
            if current_status in valid_transitions:
                if value not in valid_transitions[current_status] and value != current_status:
                    raise serializers.ValidationError(
                        f"Invalid status transition from '{current_status}' to '{value}'"
                    )
        
        return value
    
    def validate_metadata(self, value):
        """Validate metadata JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a valid JSON object.")
        
        return value
    
    def validate_results(self, value):
        """Validate results JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Results must be a valid JSON object.")
        
        return value
    
    def update(self, instance, validated_data):
        """Update sample with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['updated_by'] = str(request.user.username)
        
        return super().update(instance, validated_data)


class SampleBarcodeSerializer(serializers.ModelSerializer):
    """
    Serializer for barcode-based sample lookup.
    """
    
    user_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Sample
        fields = [
            'id', 'name', 'sample_type', 'status', 'barcode',
            'user_name', 'collection_date', 'created_at'
        ]
        read_only_fields = ['id', 'user_name', 'created_at']


class SampleStatsSerializer(serializers.Serializer):
    """
    Serializer for sample statistics.
    """
    
    total_samples = serializers.IntegerField()
    pending_samples = serializers.IntegerField()
    processing_samples = serializers.IntegerField()
    completed_samples = serializers.IntegerField()
    rejected_samples = serializers.IntegerField()
    archived_samples = serializers.IntegerField()
    samples_by_type = serializers.DictField()
    samples_by_user = serializers.DictField()
    average_processing_time = serializers.FloatField(allow_null=True)


class SampleProcessingSerializer(serializers.Serializer):
    """
    Serializer for sample processing actions.
    """
    
    action = serializers.ChoiceField(choices=['start', 'complete', 'reject', 'archive'])
    results = serializers.JSONField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    
    def validate_results(self, value):
        """Validate results for completion action."""
        action = self.initial_data.get('action')
        if action == 'complete' and value and not isinstance(value, dict):
            raise serializers.ValidationError("Results must be a valid JSON object.")
        return value 