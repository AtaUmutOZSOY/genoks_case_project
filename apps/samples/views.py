"""
Views for Sample management in tenant-specific schemas.
"""

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Sample
from .serializers import (
    SampleSerializer,
    SampleListSerializer,
    SampleCreateSerializer,
    SampleUpdateSerializer
)
from apps.common.pagination import StandardResultsSetPagination


@extend_schema_view(
    list=extend_schema(
        summary="List Samples",
        description="Get a list of all active samples in the current tenant schema.",
        tags=["Samples"]
    ),
    create=extend_schema(
        summary="Create Sample", 
        description="Create a new sample in the current tenant schema.",
        tags=["Samples"]
    ),
    retrieve=extend_schema(
        summary="Get Sample Details",
        description="Retrieve detailed information about a specific sample.",
        tags=["Samples"]
    ),
    update=extend_schema(
        summary="Update Sample",
        description="Update sample information.",
        tags=["Samples"]
    ),
    destroy=extend_schema(
        summary="Delete Sample",
        description="Delete a sample (sets is_active=False).",
        tags=["Samples"]
    ),
)
class SampleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sample CRUD operations within tenant schemas.
    
    All operations are performed within the tenant schema context
    set by the TenantMiddleware based on the center_id in the URL.
    
    Provides:
    - List samples for the current tenant
    - Create new sample
    - Retrieve sample details
    - Update sample
    - Delete sample
    """
    
    queryset = Sample.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    
    # Filtering options
    filterset_fields = ['is_active', 'status', 'sample_type', 'user_id']
    search_fields = ['name', 'description', 'barcode', 'collection_location']
    ordering_fields = ['name', 'created_at', 'collection_date', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return the appropriate serializer class based on action."""
        if self.action == 'list':
            return SampleListSerializer
        elif self.action == 'create':
            return SampleCreateSerializer
        elif self.action == 'update':
            return SampleUpdateSerializer
        else:
            return SampleSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions and request parameters."""
        queryset = self.queryset
        
        # By default, only show active samples
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        
        # Filter by date range if specified
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new sample in the current tenant schema."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Ensure we're in the correct tenant context
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response(
                    {'error': 'Tenant context not found. Please use the correct URL format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sample = serializer.save()
            
            # Return the created sample with full details
            response_serializer = SampleSerializer(sample, context={'request': request})
            
            return Response(
                {
                    'message': 'Sample created successfully',
                    'data': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to create sample',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Update sample details."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            sample = serializer.save()
            
            # Return updated sample with full details
            response_serializer = SampleSerializer(sample, context={'request': request})
            
            return Response(
                {
                    'message': 'Sample updated successfully',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to update sample',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete a sample."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'Sample "{instance.name}" has been deleted',
                    'id': instance.id
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to delete sample',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            ) 