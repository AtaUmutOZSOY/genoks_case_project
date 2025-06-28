"""
Comprehensive test suite for Samples API endpoints.
Tests multi-tenant functionality, CRUD operations, workflow states, permissions, and security.
"""

from django.urls import reverse
from rest_framework import status
from unittest.mock import patch
from datetime import datetime, timezone

from apps.samples.models import Sample
from tests.utils import (
    TenantAwareTestCase, 
    SecurityTestMixin, 
    PerformanceTestMixin,
    TestDataFactory,
    MockTimeTestMixin
)


class SamplesAPITestCase(TenantAwareTestCase, SecurityTestMixin, PerformanceTestMixin, MockTimeTestMixin):
    """Test cases for Samples API endpoints."""
    
    def setUp(self):
        super().setUp()
        self.samples_url = lambda center_id: reverse(
            'samples:sample-list', 
            kwargs={'center_id': center_id}
        )
        self.sample_detail_url = lambda center_id, pk: reverse(
            'samples:sample-detail', 
            kwargs={'center_id': center_id, 'pk': pk}
        )
        self.sample_process_url = lambda center_id, pk: reverse(
            'samples:sample-process', 
            kwargs={'center_id': center_id, 'pk': pk}
        )
        self.sample_complete_url = lambda center_id, pk: reverse(
            'samples:sample-complete', 
            kwargs={'center_id': center_id, 'pk': pk}
        )
        self.sample_reject_url = lambda center_id, pk: reverse(
            'samples:sample-reject', 
            kwargs={'center_id': center_id, 'pk': pk}
        )
        self.sample_archive_url = lambda center_id, pk: reverse(
            'samples:sample-archive', 
            kwargs={'center_id': center_id, 'pk': pk}
        )
        self.sample_stats_url = lambda center_id: reverse(
            'samples:sample-stats', 
            kwargs={'center_id': center_id}
        )
        self.sample_barcode_url = lambda center_id, barcode: reverse(
            'samples:sample-by-barcode', 
            kwargs={'center_id': center_id, 'barcode': barcode}
        )
    
    def create_test_sample(self, center, **kwargs):
        """Create a test sample in the specified center's schema."""
        sample_data = TestDataFactory.sample_data(**kwargs)
        
        with self.with_tenant_context(center):
            sample = Sample.objects.create(**sample_data)
            return sample
    
    def test_list_samples_unauthenticated(self):
        """Test that unauthenticated users cannot access samples list."""
        url = self.samples_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseUnauthorized(response)
    
    def test_list_samples_authenticated(self):
        """Test authenticated users can list samples from their center."""
        # Create test samples in tenant schema
        with self.with_tenant_context(self.test_center):
            sample1 = Sample.objects.create(
                patient_name='Patient 1',
                patient_id='P001',
                sample_type='blood',
                priority='normal'
            )
            sample2 = Sample.objects.create(
                patient_name='Patient 2',
                patient_id='P002',
                sample_type='urine',
                priority='urgent'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        self.assertGreaterEqual(data['count'], 2)
    
    def test_list_samples_wrong_center_access(self):
        """Test users cannot access samples from other centers."""
        # Authenticate user from test_center
        self.authenticate_admin()
        
        # Try to access samples from another_center
        url = self.samples_url(self.another_center.id)
        response = self.client.get(url)
        # Should be forbidden or return empty results based on implementation
        self.assertIn(response.status_code, [403, 200])
        
        if response.status_code == 200:
            data = self.get_response_data(response)
            # Should return empty results if user not from this center
            self.assertEqual(data['count'], 0)
    
    def test_list_samples_filtering_by_status(self):
        """Test samples list filtering by status."""
        with self.with_tenant_context(self.test_center):
            # Create samples with different statuses
            pending_sample = Sample.objects.create(
                patient_name='Pending Patient',
                patient_id='PP001',
                sample_type='blood',
                status='pending'
            )
            processing_sample = Sample.objects.create(
                patient_name='Processing Patient',
                patient_id='PR001',
                sample_type='blood',
                status='processing'
            )
            completed_sample = Sample.objects.create(
                patient_name='Completed Patient',
                patient_id='PC001',
                sample_type='blood',
                status='completed'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test pending filter
        response = self.client.get(url, {'status': 'pending'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for sample in data['results']:
            self.assertEqual(sample['status'], 'pending')
        
        # Test processing filter
        response = self.client.get(url, {'status': 'processing'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for sample in data['results']:
            self.assertEqual(sample['status'], 'processing')
    
    def test_list_samples_filtering_by_priority(self):
        """Test samples list filtering by priority."""
        with self.with_tenant_context(self.test_center):
            urgent_sample = Sample.objects.create(
                patient_name='Urgent Patient',
                patient_id='UP001',
                sample_type='blood',
                priority='urgent'
            )
            normal_sample = Sample.objects.create(
                patient_name='Normal Patient',
                patient_id='NP001',
                sample_type='blood',
                priority='normal'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test urgent filter
        response = self.client.get(url, {'priority': 'urgent'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for sample in data['results']:
            self.assertEqual(sample['priority'], 'urgent')
    
    def test_list_samples_search(self):
        """Test samples list search functionality."""
        with self.with_tenant_context(self.test_center):
            unique_sample = Sample.objects.create(
                patient_name='Unique Search Patient',
                patient_id='USP001',
                sample_type='blood',
                notes='Unique search notes'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test search by patient name
        response = self.client.get(url, {'search': 'Unique Search'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertGreater(data['count'], 0)
        
        # Verify search results
        found = False
        for sample in data['results']:
            if 'Unique Search' in sample['patient_name']:
                found = True
                break
        self.assertTrue(found)
    
    def test_create_sample_success(self):
        """Test successful sample creation."""
        self.authenticate_admin()
        
        sample_data = TestDataFactory.sample_data(
            patient_name='New Test Patient',
            patient_id='NTP001',
            sample_type='blood'
        )
        
        url = self.samples_url(self.test_center.id)
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'patient_name', 'patient_id', 'sample_type', 
                          'priority', 'status', 'barcode', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify UUID and timestamp fields
        self.assert_uuid_field(data, 'id')
        self.assert_timestamp_field(data, 'created_at')
        self.assert_timestamp_field(data, 'updated_at')
        
        # Verify data values
        self.assertEqual(data['patient_name'], sample_data['patient_name'])
        self.assertEqual(data['patient_id'], sample_data['patient_id'])
        self.assertEqual(data['sample_type'], sample_data['sample_type'])
        self.assertEqual(data['priority'], sample_data['priority'])
        self.assertEqual(data['status'], 'pending')  # Default status
        self.assertIsNotNone(data['barcode'])  # Should auto-generate barcode
        
        # Verify sample was created in correct tenant schema
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.get(id=data['id'])
            self.assertEqual(sample.patient_name, sample_data['patient_name'])
    
    def test_create_sample_validation_errors(self):
        """Test sample creation validation errors."""
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test missing required fields
        invalid_data = {}
        response = self.client.post(url, invalid_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('patient_name', data)
        self.assertIn('patient_id', data)
        self.assertIn('sample_type', data)
        
        # Test invalid sample type
        invalid_type_data = TestDataFactory.sample_data(
            patient_name='Invalid Type Patient',
            patient_id='ITP001',
            sample_type='invalid_type'
        )
        
        response = self.client.post(url, invalid_type_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('sample_type', data)
        
        # Test invalid priority
        invalid_priority_data = TestDataFactory.sample_data(
            patient_name='Invalid Priority Patient',
            patient_id='IPP001',
            sample_type='blood',
            priority='invalid_priority'
        )
        
        response = self.client.post(url, invalid_priority_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('priority', data)
    
    def test_create_sample_permissions(self):
        """Test sample creation permissions."""
        sample_data = TestDataFactory.sample_data(
            patient_name='Permission Test Patient',
            patient_id='PTP001',
            sample_type='blood'
        )
        url = self.samples_url(self.test_center.id)
        
        # Test unauthenticated user
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test viewer user (should be forbidden)
        self.authenticate_viewer()
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test regular user (should succeed)
        self.authenticate_regular_user()
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        sample_data['patient_id'] = 'PTP002'  # Avoid duplicate
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
    
    def test_retrieve_sample_success(self):
        """Test successful sample retrieval."""
        # Create test sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Retrieve Test Patient',
                patient_id='RTP001',
                sample_type='blood',
                priority='normal'
            )
        
        self.authenticate_admin()
        url = self.sample_detail_url(self.test_center.id, sample.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'patient_name', 'patient_id', 'sample_type', 
                          'priority', 'status', 'barcode', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify data values
        self.assertEqual(data['id'], str(sample.id))
        self.assertEqual(data['patient_name'], sample.patient_name)
        self.assertEqual(data['patient_id'], sample.patient_id)
    
    def test_update_sample_success(self):
        """Test successful sample update."""
        # Create test sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Update Test Patient',
                patient_id='UTP001',
                sample_type='blood',
                priority='normal'
            )
        
        self.authenticate_admin()
        
        update_data = {
            'priority': 'urgent',
            'notes': 'Updated notes'
        }
        
        url = self.sample_detail_url(self.test_center.id, sample.id)
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify updated values
        self.assertEqual(data['priority'], update_data['priority'])
        self.assertEqual(data['notes'], update_data['notes'])
        
        # Verify unchanged values
        self.assertEqual(data['patient_name'], sample.patient_name)
        self.assertEqual(data['sample_type'], sample.sample_type)
        
        # Verify database was updated
        with self.with_tenant_context(self.test_center):
            sample.refresh_from_db()
            self.assertEqual(sample.priority, update_data['priority'])
            self.assertEqual(sample.notes, update_data['notes'])
    
    def test_sample_workflow_process(self):
        """Test sample processing workflow."""
        # Create pending sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Workflow Test Patient',
                patient_id='WTP001',
                sample_type='blood',
                status='pending'
            )
        
        self.authenticate_admin()
        
        # Process the sample
        url = self.sample_process_url(self.test_center.id, sample.id)
        response = self.client.post(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['status'], 'processing')
        self.assertIsNotNone(data['processed_at'])
        
        # Verify database was updated
        with self.with_tenant_context(self.test_center):
            sample.refresh_from_db()
            self.assertEqual(sample.status, 'processing')
            self.assertIsNotNone(sample.processed_at)
    
    def test_sample_workflow_complete(self):
        """Test sample completion workflow."""
        # Create processing sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Complete Test Patient',
                patient_id='CTP001',
                sample_type='blood',
                status='processing'
            )
        
        self.authenticate_admin()
        
        # Complete the sample
        complete_data = {'results': 'Test results data'}
        url = self.sample_complete_url(self.test_center.id, sample.id)
        response = self.client.post(url, complete_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['results'], complete_data['results'])
        self.assertIsNotNone(data['completed_at'])
        
        # Verify database was updated
        with self.with_tenant_context(self.test_center):
            sample.refresh_from_db()
            self.assertEqual(sample.status, 'completed')
            self.assertEqual(sample.results, complete_data['results'])
            self.assertIsNotNone(sample.completed_at)
    
    def test_sample_workflow_reject(self):
        """Test sample rejection workflow."""
        # Create processing sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Reject Test Patient',
                patient_id='RTP001',
                sample_type='blood',
                status='processing'
            )
        
        self.authenticate_admin()
        
        # Reject the sample
        reject_data = {'rejection_reason': 'Sample contaminated'}
        url = self.sample_reject_url(self.test_center.id, sample.id)
        response = self.client.post(url, reject_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['status'], 'rejected')
        self.assertEqual(data['rejection_reason'], reject_data['rejection_reason'])
        self.assertIsNotNone(data['rejected_at'])
        
        # Verify database was updated
        with self.with_tenant_context(self.test_center):
            sample.refresh_from_db()
            self.assertEqual(sample.status, 'rejected')
            self.assertEqual(sample.rejection_reason, reject_data['rejection_reason'])
            self.assertIsNotNone(sample.rejected_at)
    
    def test_sample_workflow_archive(self):
        """Test sample archiving workflow."""
        # Create completed sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Archive Test Patient',
                patient_id='ATP001',
                sample_type='blood',
                status='completed'
            )
        
        self.authenticate_admin()
        
        # Archive the sample
        url = self.sample_archive_url(self.test_center.id, sample.id)
        response = self.client.post(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['status'], 'archived')
        self.assertIsNotNone(data['archived_at'])
        
        # Verify database was updated
        with self.with_tenant_context(self.test_center):
            sample.refresh_from_db()
            self.assertEqual(sample.status, 'archived')
            self.assertIsNotNone(sample.archived_at)
    
    def test_sample_workflow_invalid_transitions(self):
        """Test invalid workflow transitions are prevented."""
        # Create completed sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Invalid Transition Patient',
                patient_id='ITP001',
                sample_type='blood',
                status='completed'
            )
        
        self.authenticate_admin()
        
        # Try to process completed sample (should fail)
        url = self.sample_process_url(self.test_center.id, sample.id)
        response = self.client.post(url)
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('error', data)
    
    def test_sample_barcode_lookup(self):
        """Test sample lookup by barcode."""
        # Create sample with known barcode
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Barcode Test Patient',
                patient_id='BTP001',
                sample_type='blood',
                barcode='BC123456'
            )
        
        self.authenticate_admin()
        
        # Lookup sample by barcode
        url = self.sample_barcode_url(self.test_center.id, sample.barcode)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['id'], str(sample.id))
        self.assertEqual(data['barcode'], sample.barcode)
        self.assertEqual(data['patient_name'], sample.patient_name)
    
    def test_sample_barcode_lookup_not_found(self):
        """Test sample lookup with non-existent barcode."""
        self.authenticate_admin()
        
        url = self.sample_barcode_url(self.test_center.id, 'NONEXISTENT')
        response = self.client.get(url)
        self.assertResponseNotFound(response)
    
    def test_sample_statistics(self):
        """Test sample statistics endpoint."""
        # Create samples with different statuses
        with self.with_tenant_context(self.test_center):
            Sample.objects.create(
                patient_name='Stats Patient 1',
                patient_id='SP001',
                sample_type='blood',
                status='pending'
            )
            Sample.objects.create(
                patient_name='Stats Patient 2',
                patient_id='SP002',
                sample_type='blood',
                status='processing'
            )
            Sample.objects.create(
                patient_name='Stats Patient 3',
                patient_id='SP003',
                sample_type='blood',
                status='completed'
            )
        
        self.authenticate_admin()
        
        url = self.sample_stats_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify statistics structure
        expected_fields = ['total_samples', 'pending_samples', 'processing_samples', 
                          'completed_samples', 'rejected_samples', 'archived_samples']
        self.assert_required_fields(data, expected_fields)
        
        # Verify values are integers and make sense
        for field in expected_fields:
            self.assertIsInstance(data[field], int)
            self.assertGreaterEqual(data[field], 0)
        
        # Verify total equals sum of status counts
        status_sum = (data['pending_samples'] + data['processing_samples'] + 
                     data['completed_samples'] + data['rejected_samples'] + 
                     data['archived_samples'])
        self.assertEqual(data['total_samples'], status_sum)
    
    def test_samples_tenant_isolation(self):
        """Test that samples are properly isolated between tenants."""
        # Create samples in different tenant schemas
        with self.with_tenant_context(self.test_center):
            test_center_sample = Sample.objects.create(
                patient_name='Test Center Patient',
                patient_id='TCP001',
                sample_type='blood'
            )
        
        with self.with_tenant_context(self.another_center):
            another_center_sample = Sample.objects.create(
                patient_name='Another Center Patient',
                patient_id='ACP001',
                sample_type='blood'
            )
        
        self.authenticate_admin()
        
        # Test that test_center samples only show test_center data
        url = self.samples_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        sample_ids = [s['id'] for s in data['results']]
        
        self.assertIn(str(test_center_sample.id), sample_ids)
        self.assertNotIn(str(another_center_sample.id), sample_ids)
        
        # Test that another_center samples only show another_center data
        url = self.samples_url(self.another_center.id)
        response = self.client.get(url)
        
        if response.status_code == 200:  # If access is allowed
            data = self.get_response_data(response)
            sample_ids = [s['id'] for s in data['results']]
            
            self.assertNotIn(str(test_center_sample.id), sample_ids)
            # Note: another_center_sample might not be accessible if user is from test_center
    
    def test_samples_security_sql_injection(self):
        """Test SQL injection protection in samples endpoints."""
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test SQL injection in search parameter
        self.test_sql_injection(url, {'search': 'test'})
        
        # Test SQL injection in filter parameters
        self.test_sql_injection(url, {'status': 'pending'})
    
    def test_samples_security_xss(self):
        """Test XSS protection in samples endpoints."""
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test XSS in sample creation
        sample_data = TestDataFactory.sample_data(
            patient_name='XSS Test Patient',
            patient_id='XTP001',
            sample_type='blood'
        )
        
        self.test_xss_protection(url, sample_data)
    
    def test_samples_performance_query_count(self):
        """Test database query performance for samples list."""
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test query count for samples list
        with self.assert_query_count(4):  # Expected: auth, schema switch, samples query, count query
            response = self.client.get(url)
            self.assertResponseSuccess(response)
    
    def test_samples_ordering(self):
        """Test samples list ordering."""
        # Create samples with different creation times
        with self.with_tenant_context(self.test_center):
            old_sample = Sample.objects.create(
                patient_name='Old Patient',
                patient_id='OP001',
                sample_type='blood'
            )
            new_sample = Sample.objects.create(
                patient_name='New Patient',
                patient_id='NP001',
                sample_type='blood'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Test ordering by created_at (newest first - default)
        response = self.client.get(url, {'ordering': '-created_at'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        if len(data['results']) >= 2:
            first_created = data['results'][0]['created_at']
            second_created = data['results'][1]['created_at']
            self.assertGreaterEqual(first_created, second_created)
        
        # Test ordering by priority
        response = self.client.get(url, {'ordering': 'priority'})
        self.assertResponseSuccess(response)
    
    def test_sample_barcode_generation(self):
        """Test automatic barcode generation."""
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        sample_data = TestDataFactory.sample_data(
            patient_name='Barcode Gen Patient',
            patient_id='BGP001',
            sample_type='blood'
        )
        
        response = self.client.post(url, sample_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        data = self.get_response_data(response)
        
        # Verify barcode was generated
        self.assertIsNotNone(data['barcode'])
        self.assertNotEqual(data['barcode'], '')
        self.assertIsInstance(data['barcode'], str)
        self.assertGreaterEqual(len(data['barcode']), 6)  # Minimum barcode length
    
    def test_sample_duplicate_patient_id_same_center(self):
        """Test that duplicate patient IDs in same center are handled properly."""
        # Create first sample
        with self.with_tenant_context(self.test_center):
            first_sample = Sample.objects.create(
                patient_name='First Patient',
                patient_id='DUP001',
                sample_type='blood'
            )
        
        self.authenticate_admin()
        url = self.samples_url(self.test_center.id)
        
        # Try to create second sample with same patient_id
        duplicate_data = TestDataFactory.sample_data(
            patient_name='Second Patient',
            patient_id='DUP001',  # Same patient ID
            sample_type='urine'
        )
        
        response = self.client.post(url, duplicate_data, format='json')
        # This might succeed (multiple samples per patient) or fail (unique constraint)
        # depending on business rules
        self.assertIn(response.status_code, [201, 400])
    
    def test_sample_time_tracking(self):
        """Test sample time tracking throughout workflow."""
        # Create sample
        with self.with_tenant_context(self.test_center):
            sample = Sample.objects.create(
                patient_name='Time Track Patient',
                patient_id='TTP001',
                sample_type='blood',
                status='pending'
            )
        
        self.authenticate_admin()
        
        # Mock current time for consistent testing
        mock_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with self.mock_now(mock_time):
            # Process sample
            url = self.sample_process_url(self.test_center.id, sample.id)
            response = self.client.post(url)
            self.assertResponseSuccess(response)
            
            data = self.get_response_data(response)
            self.assertIsNotNone(data['processed_at'])
        
        # Complete sample with different time
        mock_complete_time = datetime(2023, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        
        with self.mock_now(mock_complete_time):
            complete_data = {'results': 'Test completed'}
            url = self.sample_complete_url(self.test_center.id, sample.id)
            response = self.client.post(url, complete_data, format='json')
            self.assertResponseSuccess(response)
            
            data = self.get_response_data(response)
            self.assertIsNotNone(data['completed_at'])
            
            # Verify processing time was tracked
            processed_time = datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00'))
            completed_time = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
            
            # Completed time should be after processed time
            self.assertGreater(completed_time, processed_time) 