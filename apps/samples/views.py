"""
Views for Sample management in tenant-specific schemas.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Avg
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Sample
from .serializers import (
    SampleSerializer,
    SampleListSerializer,
    SampleCreateSerializer,
    SampleUpdateSerializer,
    SampleBarcodeSerializer,
    SampleStatsSerializer,
    SampleProcessingSerializer
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
    partial_update=extend_schema(
        summary="Partial Update Sample", 
        description="Partially update sample information.",
        tags=["Samples"]
    ),
    destroy=extend_schema(
        summary="Soft Delete Sample",
        description="Soft delete a sample (sets is_active=False).",
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
    - Delete sample (soft delete)
    - Processing actions (start, complete, reject, archive)
    """
    
    queryset = Sample.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
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
        elif self.action in ['update', 'partial_update']:
            return SampleUpdateSerializer
        elif self.action == 'by_barcode':
            return SampleBarcodeSerializer
        elif self.action == 'process':
            return SampleProcessingSerializer
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
        """Soft delete a sample."""
        instance = self.get_object()
        
        try:
            # Perform soft delete
            instance.soft_delete(user=request.user)
            
            return Response(
                {
                    'message': f'Sample "{instance.name}" has been deactivated',
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
    
    @extend_schema(
        summary="Restore Soft Deleted Sample",
        description="Restore a soft deleted sample (sets is_active=True).",
        tags=["Samples"],
        responses={200: {'description': 'Sample restored successfully'}}
    )
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted sample."""
        sample = self.get_object()
        
        if sample.is_active:
            return Response(
                {'message': 'Sample is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sample.restore(user=request.user)
            
            response_serializer = SampleSerializer(sample, context={'request': request})
            
            return Response(
                {
                    'message': f'Sample "{sample.name}" has been restored',
                    'data': response_serializer.data
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to restore sample',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Process Sample",
        description="Handle sample processing actions: start, complete, reject, or archive.",
        tags=["Samples"],
        responses={200: {'description': 'Sample processing action completed successfully'}}
    )
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Handle sample processing actions."""
        sample = self.get_object()
        serializer = SampleProcessingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        results = serializer.validated_data.get('results')
        reason = serializer.validated_data.get('reason')
        
        try:
            if action_type == 'start':
                sample.start_processing(user=request.user)
                message = f'Sample "{sample.name}" processing started'
            
            elif action_type == 'complete':
                sample.complete_processing(results=results, user=request.user)
                message = f'Sample "{sample.name}" processing completed'
            
            elif action_type == 'reject':
                sample.reject_sample(reason=reason, user=request.user)
                message = f'Sample "{sample.name}" has been rejected'
            
            elif action_type == 'archive':
                sample.archive_sample(user=request.user)
                message = f'Sample "{sample.name}" has been archived'
            
            response_serializer = SampleSerializer(sample, context={'request': request})
            
            return Response(
                {
                    'message': message,
                    'data': response_serializer.data
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
                    'error': f'Failed to {action_type} sample',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Sample by Barcode",
        description="Retrieve a sample by its barcode identifier.",
        tags=["Samples"],
        responses={200: {'description': 'Sample found by barcode'}}
    )
    @action(detail=False, methods=['get'])
    def by_barcode(self, request):
        """Get sample by barcode."""
        barcode = request.query_params.get('barcode')
        
        if not barcode:
            return Response(
                {'error': 'Barcode parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sample = Sample.get_by_barcode(barcode)
            
            if not sample:
                return Response(
                    {'error': 'Sample not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = SampleBarcodeSerializer(sample, context={'request': request})
            
            return Response({'data': serializer.data})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get sample by barcode',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Samples by User",
        description="Get all samples created by a specific user.",
        tags=["Samples"],
        responses={200: {'description': 'Samples filtered by user'}}
    )
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get samples by user ID."""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            samples = Sample.get_samples_by_user(user_id)
            serializer = SampleListSerializer(samples, many=True, context={'request': request})
            
            return Response({
                'count': samples.count(),
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get samples by user',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Samples by Status",
        description="Get samples grouped by their processing status.",
        tags=["Samples"],
        responses={200: {'description': 'Samples grouped by status'}}
    )
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get samples grouped by status."""
        try:
            result = {}
            
            for status_code, status_name in Sample.STATUS_CHOICES:
                samples = Sample.get_samples_by_status(status_code)
                serializer = SampleListSerializer(samples, many=True, context={'request': request})
                
                result[status_name] = {
                    'status_code': status_code,
                    'count': samples.count(),
                    'samples': serializer.data
                }
            
            return Response({'data': result})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get samples by status',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Samples by Type",
        description="Get samples grouped by their sample type (blood, urine, tissue, etc.).",
        tags=["Samples"],
        responses={200: {'description': 'Samples grouped by type'}}
    )
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get samples grouped by type."""
        try:
            result = {}
            
            for type_code, type_name in Sample.SAMPLE_TYPE_CHOICES:
                samples = Sample.get_samples_by_type(type_code)
                serializer = SampleListSerializer(samples, many=True, context={'request': request})
                
                result[type_name] = {
                    'type_code': type_code,
                    'count': samples.count(),
                    'samples': serializer.data
                }
            
            return Response({'data': result})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get samples by type',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="Get Sample Statistics",
        description="Get statistical information about samples in the current tenant.",
        tags=["Samples"],
        responses={200: {'description': 'Sample statistics'}}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get comprehensive statistics for samples."""
        try:
            # Basic counts
            total_samples = Sample.objects.count()
            pending_samples = Sample.objects.filter(status='pending').count()
            processing_samples = Sample.objects.filter(status='processing').count()
            completed_samples = Sample.objects.filter(status='completed').count()
            rejected_samples = Sample.objects.filter(status='rejected').count()
            archived_samples = Sample.objects.filter(status='archived').count()
            
            # Count by type
            samples_by_type = {}
            for type_code, type_name in Sample.SAMPLE_TYPE_CHOICES:
                count = Sample.objects.filter(sample_type=type_code).count()
                samples_by_type[type_name] = count
            
            # Count by user
            samples_by_user = {}
            user_counts = Sample.objects.values('user_id').annotate(count=Count('id'))
            
            for item in user_counts:
                user_id = item['user_id']
                count = item['count']
                
                # Get user name
                try:
                    from apps.users.models import User
                    user = User.objects.get(id=user_id)
                    user_name = user.get_full_name()
                except User.DoesNotExist:
                    user_name = "Unknown User"
                
                samples_by_user[user_name] = count
            
            # Calculate average processing time
            completed_with_times = Sample.objects.filter(
                status='completed',
                processing_started__isnull=False,
                processing_completed__isnull=False
            )
            
            avg_processing_time = None
            if completed_with_times.exists():
                total_time = 0
                count = 0
                
                for sample in completed_with_times:
                    if sample.processing_started and sample.processing_completed:
                        delta = sample.processing_completed - sample.processing_started
                        total_time += delta.total_seconds()
                        count += 1
                
                if count > 0:
                    avg_processing_time = total_time / count / 3600  # Convert to hours
            
            stats_data = {
                'total_samples': total_samples,
                'pending_samples': pending_samples,
                'processing_samples': processing_samples,
                'completed_samples': completed_samples,
                'rejected_samples': rejected_samples,
                'archived_samples': archived_samples,
                'samples_by_type': samples_by_type,
                'samples_by_user': samples_by_user,
                'average_processing_time': avg_processing_time
            }
            
            serializer = SampleStatsSerializer(data=stats_data)
            serializer.is_valid(raise_exception=True)
            
            return Response({'data': serializer.data})
            
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to get sample statistics',
                    'details': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            ) 