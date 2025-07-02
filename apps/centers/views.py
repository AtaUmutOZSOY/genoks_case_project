"""
Views for Center management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Center
from .serializers import (
    CenterSerializer,
    CenterListSerializer,
    CenterCreateSerializer,
    CenterUpdateSerializer,
    CenterDetailSerializer
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
    destroy=extend_schema(
        summary="Delete Center",
        description="Delete a center (sets is_active=False).",
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
    - Delete center
    """
    
    queryset = Center.all_objects.all()  # Use all_objects to include soft-deleted centers
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    
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
        elif self.action == 'update':
            return CenterUpdateSerializer
        elif self.action == 'retrieve':
            return CenterDetailSerializer
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
        """Delete a center."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'Center "{instance.name}" has been deleted',
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