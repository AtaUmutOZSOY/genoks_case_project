"""
Views for User management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import User
from .serializers import (
    UserSerializer,
    UserListSerializer,
    UserCreateSerializer,
    UserUpdateSerializer
)
from apps.centers.models import Center
from apps.common.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="List Users",
        description="Get a list of all active users in the system.",
        tags=["Users"]
    ),
    create=extend_schema(
        summary="Create User", 
        description="Create a new user and assign them to a center.",
        tags=["Users"]
    ),
    retrieve=extend_schema(
        summary="Get User Details",
        description="Retrieve detailed information about a specific user.",
        tags=["Users"]
    ),
    update=extend_schema(
        summary="Update User",
        description="Update user information.",
        tags=["Users"]
    ),
    destroy=extend_schema(
        summary="Delete User",
        description="Delete a user (sets is_active=False).",
        tags=["Users"]
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User CRUD operations.
    
    Provides:
    - List all users
    - Create new user
    - Retrieve user details
    - Update user
    - Delete user
    """
    
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    
    # Filtering options
    filterset_fields = ['is_active', 'role', 'center']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'first_name', 'last_name', 'created_at']
    ordering = ['first_name', 'last_name']
    
    def get_serializer_class(self):
        """Return the appropriate serializer class based on action."""
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'update':
            return UserUpdateSerializer
        else:
            return UserSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and request parameters."""
        queryset = self.queryset
        
        # By default, only show active users
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        
        # Filter by center if specified
        center_id = self.request.query_params.get('center_id')
        if center_id:
            try:
                center = Center.objects.get(id=center_id)
                queryset = queryset.filter(center=center)
            except Center.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new user."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            
            # Return the created user with full details
            response_serializer = UserSerializer(user, context={'request': request})
            
            # Get login info for message
            login_info = getattr(user, '_login_info', None)
            if login_info:
                message = (f'User created successfully. '
                          f'Login credentials - Username: {login_info["username"]}, '
                          f'Password: {login_info["password"]}')
            else:
                message = 'User created successfully'
            
            return Response(
                {
                    'message': message,
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to create user',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Update user details."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = serializer.save()
            
            # Return updated user with full details
            response_serializer = UserSerializer(user, context={'request': request})
            
            return Response(
                {
                    'message': 'User updated successfully',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to update user',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a user."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'User "{instance.username}" has been deleted',
                    'id': instance.id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to delete user',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            ) 