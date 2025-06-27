"""
Views for Center management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Center
from .serializers import (
    CenterSerializer,
    CenterListSerializer,
    CenterCreateSerializer,
    CenterUpdateSerializer,
    CenterDetailSerializer,
    CenterStatsSerializer
)
from apps.common.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="List Centers",
        description="Get a list of all active centers in the system.",
        tags=["Centers"]
    ),
    create=extend_schema(
        summary="Create Center", 
        description="Create a new center. This will automatically create a dedicated database schema for the center.",
        tags=["Centers"]
    ),
    retrieve=extend_schema(
        summary="Get Center Details",
        description="Retrieve detailed information about a specific center.",
        tags=["Centers"]
    ),
    update=extend_schema(
        summary="Update Center",
        description="Update center information.",
        tags=["Centers"]
    ),
    partial_update=extend_schema(
        summary="Partial Update Center", 
        description="Partially update center information.",
        tags=["Centers"]
    ),
    destroy=extend_schema(
        summary="Soft Delete Center",
        description="Soft delete a center (sets is_active=False). The center's data and schema are preserved.",
        tags=["Centers"]
    ),
)
class CenterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Center CRUD operations.
    
    Provides:
    - List all centers
    - Create new center
    - Retrieve center details
    - Update center
    - Delete center (soft delete)
    """
    
    queryset = Center.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Filtering options
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return the appropriate serializer class based on action."""
        if self.action == 'list':
            return CenterListSerializer
        elif self.action == 'create':
            return CenterCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CenterUpdateSerializer
        elif self.action == 'retrieve':
            return CenterDetailSerializer
        elif self.action == 'stats':
            return CenterStatsSerializer
        else:
            return CenterSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and request parameters."""
        queryset = self.queryset
        
        # By default, only show active centers
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new center with schema generation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            center = serializer.save()
            
            # Return the created center with full details
            response_serializer = CenterSerializer(center, context={'request': request})
            
            return Response(
                {
                    'message': 'Center created successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to create center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Update center details."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            center = serializer.save()
            
            # Return updated center with full details
            response_serializer = CenterSerializer(center, context={'request': request})
            
            return Response(
                {
                    'message': 'Center updated successfully',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to update center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a center."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'Center "{instance.name}" has been deactivated',
                    'id': instance.id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to delete center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Restore Soft Deleted Center",
        description="Restore a soft deleted center (sets is_active=True).",
        tags=["Centers"],
        responses={200: {'description': 'Center restored successfully'}}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted center."""
        center = self.get_object()
        
        if center.is_active:
            return Response(
                {'message': 'Center is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            center.restore(user=request.user)
            
            response_serializer = CenterSerializer(center, context={'request': request})
            
            return Response(
                {
                    'message': f'Center "{center.name}" has been restored',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to restore center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Hard Delete Center", 
        description="Permanently delete a center and its database schema. WARNING: This action cannot be undone!",
        tags=["Centers"],
        responses={204: {'description': 'Center permanently deleted'}}
    )
    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        """Permanently delete a center and its schema."""
        center = self.get_object()
        center_name = center.name
        
        try:
            center.hard_delete()
            
            return Response(
                {
                    'message': f'Center "{center_name}" has been permanently deleted',
                    'warning': 'All data associated with this center has been removed'
                },
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to permanently delete center',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Center Statistics",
        description="Get statistical information about a center including user count and sample count.",
        tags=["Centers"],
        responses={200: CenterStatsSerializer}
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get detailed statistics for a center."""
        center = self.get_object()
        
        try:
            stats = {
                'center_id': center.id,
                'center_name': center.name,
                'schema_name': center.schema_name,
                'sample_count': center.get_sample_count(),
                'user_count': center.get_user_count(),
                'created_at': center.created_at,
                'last_updated': center.updated_at,
                'is_active': center.is_active,
                'settings': center.settings
            }
            
            serializer = self.get_serializer(stats)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get center statistics',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Centers Summary",
        description="Get summary statistics for all centers.",
        tags=["Centers"],
        responses={200: {
            'type': 'object',
            'properties': {
                'total_centers': {'type': 'integer'},
                'active_centers': {'type': 'integer'},
                'total_users': {'type': 'integer'},
                'centers': {'type': 'array', 'items': {'$ref': '#/components/schemas/CenterStats'}}
            }
        }}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for all centers."""
        try:
            total_centers = Center.objects.count()
            active_centers = Center.objects.filter(is_active=True).count()
            inactive_centers = total_centers - active_centers
            
            # Get sample counts (this might be slow for many centers)
            total_samples = 0
            for center in Center.objects.filter(is_active=True):
                total_samples += center.get_sample_count()
            
            # Get user counts
            from apps.users.models import User
            total_users = User.objects.filter(is_active=True).count()
            
            summary = {
                'total_centers': total_centers,
                'active_centers': active_centers,
                'inactive_centers': inactive_centers,
                'total_samples': total_samples,
                'average_samples_per_center': total_samples / active_centers if active_centers > 0 else 0,
                'total_users': total_users
            }
            
            centers_stats = []
            for center in Center.objects.filter(is_active=True):
                centers_stats.append({
                    'id': center.id,
                    'name': center.name,
                    'user_count': center.get_user_count(),
                    'sample_count': center.get_sample_count(),
                    'created_at': center.created_at,
                    'is_active': center.is_active,
                })
            
            summary['centers'] = centers_stats
            
            return Response({'data': summary})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get centers summary',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            ) 