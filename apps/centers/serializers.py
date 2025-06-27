"""
Serializers for Center model.
"""

from rest_framework import serializers
from apps.common.serializers import BaseModelSerializer
from .models import Center


class CenterSerializer(serializers.ModelSerializer):
    """
    Basic serializer for Center model.
    """
    
    class Meta:
        model = Center
        fields = [
            'id', 'name', 'schema_name', 'description', 'settings',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CenterDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Center model with additional computed fields.
    """
    user_count = serializers.SerializerMethodField()
    sample_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Center
        fields = [
            'id', 'name', 'schema_name', 'description', 'settings',
            'user_count', 'sample_count',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_count', 'sample_count']
    
    def get_user_count(self, obj):
        """Get the number of users in this center."""
        return obj.get_user_count()
    
    def get_sample_count(self, obj):
        """Get the number of samples in this center."""
        return obj.get_sample_count()


class CenterCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new Center.
    """
    
    class Meta:
        model = Center
        fields = ['name', 'description', 'settings']
    
    def validate_name(self, value):
        """Validate center name."""
        if Center.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A center with this name already exists.")
        return value


class CenterUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing Center.
    """
    
    class Meta:
        model = Center
        fields = ['name', 'description', 'settings']
    
    def validate_name(self, value):
        """Validate center name (exclude current instance)."""
        instance = getattr(self, 'instance', None)
        if instance and Center.objects.filter(name__iexact=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("A center with this name already exists.")
        return value


class CenterStatsSerializer(serializers.Serializer):
    """
    Serializer for center statistics.
    """
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    user_count = serializers.IntegerField(read_only=True)
    sample_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class CenterListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing centers.
    """
    
    class Meta:
        model = Center
        fields = ['id', 'name', 'schema_name', 'is_active', 'created_at']


class CenterListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for Center list views.
    """
    
    user_count = serializers.ReadOnlyField(source='get_user_count')
    
    class Meta:
        model = Center
        fields = [
            'id', 'name', 'description', 'user_count',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_count']


class CenterCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new centers.
    """
    
    class Meta:
        model = Center
        fields = ['name', 'description', 'settings']
    
    def validate_name(self, value):
        """Validate center name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Center name must be at least 2 characters long.")
        
        # Check for uniqueness
        if Center.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("A center with this name already exists.")
        
        return value.strip()
    
    def validate_settings(self, value):
        """Validate settings JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a valid JSON object.")
        
        return value
    
    def create(self, validated_data):
        """Create center with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = str(request.user.username)
            validated_data['updated_by'] = str(request.user.username)
        
        return Center.objects.create(**validated_data)


class CenterUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating centers.
    """
    
    class Meta:
        model = Center
        fields = ['name', 'description', 'settings', 'is_active']
    
    def validate_name(self, value):
        """Validate center name."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Center name must be at least 2 characters long.")
        
        # Check for uniqueness (excluding current instance)
        queryset = Center.objects.filter(name__iexact=value.strip())
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A center with this name already exists.")
        
        return value.strip()
    
    def validate_settings(self, value):
        """Validate settings JSON field."""
        if value is None:
            return {}
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a valid JSON object.")
        
        return value
    
    def update(self, instance, validated_data):
        """Update center with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['updated_by'] = str(request.user.username)
        
        return super().update(instance, validated_data) 