"""
Serializers for User model.
"""

from rest_framework import serializers
from apps.common.serializers import BaseModelSerializer
from apps.centers.models import Center
from .models import User


class UserSerializer(BaseModelSerializer):
    """
    Serializer for User model with full details.
    """
    
    # Add computed fields
    full_name = serializers.ReadOnlyField()
    center_name = serializers.ReadOnlyField()
    center_schema = serializers.ReadOnlyField()
    sample_count = serializers.ReadOnlyField(source='get_sample_count')
    
    # Include center details
    center_details = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = BaseModelSerializer.Meta.fields + [
            'username', 'email', 'first_name', 'last_name', 'phone',
            'center', 'role', 'full_name', 'center_name', 'center_schema',
            'sample_count', 'center_details'
        ]
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + [
            'full_name', 'center_name', 'center_schema', 'sample_count'
        ]
    
    def get_center_details(self, obj):
        """Get basic center information."""
        if obj.center:
            return {
                'id': obj.center.id,
                'name': obj.center.name,
                'schema_name': obj.center.schema_name
            }
        return None
    
    def validate_username(self, value):
        """Validate username."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        value = value.lower().strip()
        
        # Check for uniqueness (excluding current instance if updating)
        queryset = User.objects.filter(username=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        return value
    
    def validate_email(self, value):
        """Validate email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        value = value.lower().strip()
        
        # Check for uniqueness (excluding current instance if updating)
        queryset = User.objects.filter(email=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value
    
    def validate_center(self, value):
        """Validate center assignment."""
        if not value:
            raise serializers.ValidationError("Center is required.")
        
        if not value.is_active:
            raise serializers.ValidationError("Cannot assign user to an inactive center.")
        
        return value
    
    def validate_role(self, value):
        """Validate role."""
        if value not in dict(User.ROLE_CHOICES):
            raise serializers.ValidationError(f"Invalid role. Must be one of: {', '.join(dict(User.ROLE_CHOICES).keys())}")
        
        return value


class UserListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for User list views.
    """
    
    full_name = serializers.ReadOnlyField()
    center_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'role',
            'center_name', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'full_name', 'center_name', 'created_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    """
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'phone', 'center', 'role'
        ]
    
    def validate_username(self, value):
        """Validate username."""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        value = value.lower().strip()
        
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        return value
    
    def validate_email(self, value):
        """Validate email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        value = value.lower().strip()
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value
    
    def validate_center(self, value):
        """Validate center assignment."""
        if not value:
            raise serializers.ValidationError("Center is required.")
        
        if not value.is_active:
            raise serializers.ValidationError("Cannot assign user to an inactive center.")
        
        return value
    
    def validate_role(self, value):
        """Validate role."""
        if value not in dict(User.ROLE_CHOICES):
            raise serializers.ValidationError(f"Invalid role. Must be one of: {', '.join(dict(User.ROLE_CHOICES).keys())}")
        
        return value
    
    def create(self, validated_data):
        """Create user with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = str(request.user.username)
            validated_data['updated_by'] = str(request.user.username)
        
        return User.objects.create(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating users.
    """
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 
            'center', 'role', 'is_active'
        ]
    
    def validate_email(self, value):
        """Validate email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        
        value = value.lower().strip()
        
        # Check for uniqueness (excluding current instance)
        queryset = User.objects.filter(email=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A user with this email already exists.")
        
        return value
    
    def validate_center(self, value):
        """Validate center assignment."""
        if not value:
            raise serializers.ValidationError("Center is required.")
        
        if not value.is_active:
            raise serializers.ValidationError("Cannot assign user to an inactive center.")
        
        return value
    
    def validate_role(self, value):
        """Validate role."""
        if value not in dict(User.ROLE_CHOICES):
            raise serializers.ValidationError(f"Invalid role. Must be one of: {', '.join(dict(User.ROLE_CHOICES).keys())}")
        
        return value
    
    def update(self, instance, validated_data):
        """Update user with audit fields."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['updated_by'] = str(request.user.username)
        
        return super().update(instance, validated_data)


class CenterUsersSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users within a specific center.
    """
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'role',
            'phone', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'full_name', 'created_at'] 