"""
Common serializers for multi-tenant application.
"""

from rest_framework import serializers
from django.utils import timezone


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for models inheriting from BaseModel.
    Provides common functionality and read-only fields.
    """
    
    # Make audit fields read-only
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
    
    class Meta:
        fields = ['id', 'created_at', 'updated_at', 'is_active', 'created_by', 'updated_by']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def create(self, validated_data):
        """Override create to set audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = str(request.user.username)
            validated_data['updated_by'] = str(request.user.username)
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Override update to set updated_by field."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['updated_by'] = str(request.user.username)
        
        return super().update(instance, validated_data)


class TimestampedModelSerializer(serializers.ModelSerializer):
    """
    Serializer for models that only need timestamp fields.
    Useful for models that don't inherit from BaseModel but need timestamps.
    """
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at'] 