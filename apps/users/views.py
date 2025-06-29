"""
Views for User management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
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
    UserUpdateSerializer,
    CenterUsersSerializer
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
    partial_update=extend_schema(
        summary="Partial Update User", 
        description="Partially update user information.",
        tags=["Users"]
    ),
    destroy=extend_schema(
        summary="Soft Delete User",
        description="Soft delete a user (sets is_active=False).",
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
    - Delete user (soft delete)
    """
    
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
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
        elif self.action in ['update', 'partial_update']:
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
            
            return Response(
                {
                    'message': 'User created successfully',
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
        """Soft delete a user."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'User "{instance.username}" has been deactivated',
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
    
    @extend_schema(
        summary="Restore Soft Deleted User",
        description="Restore a soft deleted user (sets is_active=True).",
        tags=["Users"],
        responses={200: {'description': 'User restored successfully'}}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted user."""
        user = self.get_object()
        
        if user.is_active:
            return Response(
                {'message': 'User is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user.restore(user=request.user)
            
            response_serializer = UserSerializer(user, context={'request': request})
            
            return Response(
                {
                    'message': f'User "{user.username}" has been restored',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to restore user',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Change User Center",
        description="Change the center assignment of a user.",
        tags=["Users"],
        responses={200: {'description': 'User center changed successfully'}}
    )
    @action(detail=True, methods=['post'])
    def change_center(self, request, pk=None):
        """Change user's center assignment."""
        user = self.get_object()
        center_id = request.data.get('center_id')
        
        if not center_id:
            return Response(
                {'error': 'center_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_center = Center.objects.get(id=center_id, is_active=True)
            
            change_info = user.change_center(new_center, user=request.user)
            
            response_serializer = UserSerializer(user, context={'request': request})
            
            return Response(
                {
                    'message': f'User center changed from "{change_info["old_center"]}" to "{change_info["new_center"]}"',
                    'data': response_serializer.data,
                    'change_info': change_info
                }
            )
            
        except Center.DoesNotExist:
            return Response(
                {'error': 'Center not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to change user center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Change User Role",
        description="Change the role of a user (admin, user, viewer).",
        tags=["Users"],
        responses={200: {'description': 'User role changed successfully'}}
    )
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change user's role."""
        user = self.get_object()
        new_role = request.data.get('role')
        
        if not new_role:
            return Response(
                {'error': 'role is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            change_info = user.update_role(new_role, user=request.user)
            
            response_serializer = UserSerializer(user, context={'request': request})
            
            return Response(
                {
                    'message': f'User role changed from "{change_info["old_role"]}" to "{change_info["new_role"]}"',
                    'data': response_serializer.data,
                    'change_info': change_info
                }
            )
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to change user role',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Users by Center",
        description="Get users grouped by their assigned centers.",
        tags=["Users"],
        responses={200: {'description': 'Users grouped by center'}}
    )
    @action(detail=False, methods=['get'])
    def by_center(self, request):
        """Get users grouped by center."""
        try:
            # Get all active centers
            centers = Center.objects.filter(is_active=True)
            
            result = {}
            for center in centers:
                users = User.get_users_by_center(center)
                serializer = CenterUsersSerializer(users, many=True)
                result[center.name] = {
                    'center_id': center.id,
                    'center_name': center.name,
                    'user_count': users.count(),
                    'users': serializer.data
                }
            
            return Response({'data': result})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get users by center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Users Summary",
        description="Get summary statistics for all users including counts by role and center.",
        tags=["Users"],
        responses={200: {'description': 'User summary statistics'}}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for users."""
        try:
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            inactive_users = total_users - active_users
            
            # Count by role
            role_counts = {}
            for role_key, role_name in User.ROLE_CHOICES:
                count = User.objects.filter(role=role_key, is_active=True).count()
                role_counts[role_name] = count
            
            # Count by center
            center_counts = {}
            for center in Center.objects.filter(is_active=True):
                count = User.get_users_by_center(center).count()
                center_counts[center.name] = count
            
            summary = {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'users_by_role': role_counts,
                'users_by_center': center_counts
            }
            
            return Response({'data': summary})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get user summary',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            ) 