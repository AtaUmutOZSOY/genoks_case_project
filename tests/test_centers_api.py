"""
Comprehensive test suite for Centers API endpoints.
Tests CRUD operations, permissions, validation, pagination, soft delete, and security.
"""

from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from unittest.mock import patch
from datetime import datetime, timezone

from apps.centers.models import Center
from apps.users.models import User
from tests.utils import (
    BaseAPITestCase, 
    SecurityTestMixin, 
    PerformanceTestMixin,
    TestDataFactory
)


class CentersAPITestCase(BaseAPITestCase, SecurityTestMixin, PerformanceTestMixin):
    """Test cases for Centers API endpoints."""
    
    def setUp(self):
        super().setUp()
        self.centers_url = reverse('centers:center-list')
        self.center_detail_url = lambda pk: reverse('centers:center-detail', kwargs={'pk': pk})
        self.center_stats_url = lambda pk: reverse('centers:center-stats', kwargs={'pk': pk})
        self.center_summary_url = reverse('centers:centers-summary')
        self.center_restore_url = lambda pk: reverse('centers:center-restore', kwargs={'pk': pk})
    
    def test_list_centers_unauthenticated(self):
        """Test that unauthenticated users cannot access centers list."""
        response = self.client.get(self.centers_url)
        self.assertResponseUnauthorized(response)
    
    def test_list_centers_authenticated(self):
        """Test authenticated users can list centers."""
        self.authenticate_admin()
        response = self.client.get(self.centers_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        self.assertGreaterEqual(data['count'], 2)  # At least our test centers
    
    def test_list_centers_pagination(self):
        """Test centers list pagination."""
        # Create additional centers for pagination testing
        for i in range(15):
            self.create_test_center(
                name=f'Test Center {i}',
                code=f'TC{i:03d}',
                address=f'Address {i}'
            )
        
        self.authenticate_admin()
        
        # Test first page
        response = self.client.get(self.centers_url, {'page_size': 10})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        self.assertEqual(len(data['results']), 10)
        self.assertIsNotNone(data['next'])
        self.assertIsNone(data['previous'])
        
        # Test second page
        response = self.client.get(self.centers_url, {'page': 2, 'page_size': 10})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        self.assertGreaterEqual(len(data['results']), 7)  # Remaining centers
        self.assertIsNone(data['next'])
        self.assertIsNotNone(data['previous'])
    
    def test_list_centers_filtering(self):
        """Test centers list filtering."""
        # Create centers with different statuses
        active_center = self.create_test_center(
            name='Active Center',
            code='AC001',
            address='Active Address',
            is_active=True
        )
        inactive_center = self.create_test_center(
            name='Inactive Center',
            code='IC001',
            address='Inactive Address',
            is_active=False
        )
        
        self.authenticate_admin()
        
        # Test active filter
        response = self.client.get(self.centers_url, {'is_active': 'true'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        active_centers = [c for c in data['results'] if c['is_active']]
        self.assertEqual(len(active_centers), len(data['results']))
        
        # Test inactive filter
        response = self.client.get(self.centers_url, {'is_active': 'false'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        inactive_centers = [c for c in data['results'] if not c['is_active']]
        self.assertEqual(len(inactive_centers), len(data['results']))
    
    def test_list_centers_search(self):
        """Test centers list search functionality."""
        search_center = self.create_test_center(
            name='Unique Search Center',
            code='USC001',
            address='Unique Address'
        )
        
        self.authenticate_admin()
        
        # Test search by name
        response = self.client.get(self.centers_url, {'search': 'Unique'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertGreater(data['count'], 0)
        
        # Verify search results contain the search term
        for center in data['results']:
            self.assertTrue(
                'Unique' in center['name'] or 
                'Unique' in center['code'] or 
                'Unique' in center['address']
            )
    
    def test_create_center_success(self):
        """Test successful center creation."""
        self.authenticate_admin()
        
        center_data = TestDataFactory.center_data(
            name='New Test Center',
            code='NTC001',
            address='New Test Address',
            phone='987-654-3210',
            email='new@test.com'
        )
        
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'name', 'code', 'address', 'phone', 'email', 
                          'is_active', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify UUID and timestamp fields
        self.assert_uuid_field(data, 'id')
        self.assert_timestamp_field(data, 'created_at')
        self.assert_timestamp_field(data, 'updated_at')
        
        # Verify data values
        self.assertEqual(data['name'], center_data['name'])
        self.assertEqual(data['code'], center_data['code'])
        self.assertEqual(data['address'], center_data['address'])
        self.assertEqual(data['phone'], center_data['phone'])
        self.assertEqual(data['email'], center_data['email'])
        self.assertTrue(data['is_active'])
        
        # Verify center was created in database
        center = Center.objects.get(id=data['id'])
        self.assertEqual(center.name, center_data['name'])
        self.assertEqual(center.code, center_data['code'])
    
    def test_create_center_validation_errors(self):
        """Test center creation validation errors."""
        self.authenticate_admin()
        
        # Test missing required fields
        invalid_data = {}
        response = self.client.post(self.centers_url, invalid_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('name', data)
        self.assertIn('code', data)
        self.assertIn('address', data)
        
        # Test duplicate code
        duplicate_data = TestDataFactory.center_data(
            name='Duplicate Center',
            code=self.test_center.code,  # Use existing code
            address='Duplicate Address'
        )
        
        response = self.client.post(self.centers_url, duplicate_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('code', data)
        
        # Test invalid email format
        invalid_email_data = TestDataFactory.center_data(
            name='Invalid Email Center',
            code='IEC001',
            address='Invalid Email Address',
            email='invalid-email'
        )
        
        response = self.client.post(self.centers_url, invalid_email_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('email', data)
    
    def test_create_center_permissions(self):
        """Test center creation permissions."""
        center_data = TestDataFactory.center_data(
            name='Permission Test Center',
            code='PTC001',
            address='Permission Test Address'
        )
        
        # Test unauthenticated user
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test regular user (should be forbidden)
        self.authenticate_regular_user()
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test viewer user (should be forbidden)
        self.authenticate_viewer()
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
    
    def test_retrieve_center_success(self):
        """Test successful center retrieval."""
        self.authenticate_admin()
        
        url = self.center_detail_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'name', 'code', 'address', 'phone', 'email', 
                          'is_active', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify data values
        self.assertEqual(data['id'], str(self.test_center.id))
        self.assertEqual(data['name'], self.test_center.name)
        self.assertEqual(data['code'], self.test_center.code)
    
    def test_retrieve_center_not_found(self):
        """Test center retrieval with non-existent ID."""
        self.authenticate_admin()
        
        from uuid import uuid4
        non_existent_id = uuid4()
        url = self.center_detail_url(non_existent_id)
        response = self.client.get(url)
        self.assertResponseNotFound(response)
    
    def test_update_center_success(self):
        """Test successful center update."""
        self.authenticate_admin()
        
        update_data = {
            'name': 'Updated Center Name',
            'address': 'Updated Address',
            'phone': '555-123-4567'
        }
        
        url = self.center_detail_url(self.test_center.id)
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify updated values
        self.assertEqual(data['name'], update_data['name'])
        self.assertEqual(data['address'], update_data['address'])
        self.assertEqual(data['phone'], update_data['phone'])
        
        # Verify unchanged values
        self.assertEqual(data['code'], self.test_center.code)
        self.assertEqual(data['email'], self.test_center.email)
        
        # Verify database was updated
        self.test_center.refresh_from_db()
        self.assertEqual(self.test_center.name, update_data['name'])
        self.assertEqual(self.test_center.address, update_data['address'])
        self.assertEqual(self.test_center.phone, update_data['phone'])
    
    def test_update_center_validation_errors(self):
        """Test center update validation errors."""
        self.authenticate_admin()
        
        # Test duplicate code
        invalid_data = {
            'code': self.another_center.code  # Use another center's code
        }
        
        url = self.center_detail_url(self.test_center.id)
        response = self.client.patch(url, invalid_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('code', data)
    
    def test_delete_center_soft_delete(self):
        """Test center soft delete functionality."""
        self.authenticate_admin()
        
        url = self.center_detail_url(self.test_center.id)
        response = self.client.delete(url)
        self.assertResponseSuccess(response, status.HTTP_204_NO_CONTENT)
        
        # Verify center is soft deleted
        self.test_center.refresh_from_db()
        self.assertIsNotNone(self.test_center.deleted_at)
        self.assertFalse(self.test_center.is_active)
        
        # Verify center is not in active list
        response = self.client.get(self.centers_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        center_ids = [c['id'] for c in data['results']]
        self.assertNotIn(str(self.test_center.id), center_ids)
    
    def test_restore_center_success(self):
        """Test center restore functionality."""
        self.authenticate_admin()
        
        # First, soft delete the center
        self.test_center.soft_delete()
        self.test_center.refresh_from_db()
        self.assertIsNotNone(self.test_center.deleted_at)
        
        # Now restore it
        url = self.center_restore_url(self.test_center.id)
        response = self.client.post(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'Center restored successfully')
        
        # Verify center is restored
        self.test_center.refresh_from_db()
        self.assertIsNone(self.test_center.deleted_at)
        self.assertTrue(self.test_center.is_active)
    
    def test_center_statistics(self):
        """Test center statistics endpoint."""
        self.authenticate_admin()
        
        # Create some test data for statistics
        # This would require creating samples in tenant schema
        # For now, test the endpoint structure
        
        url = self.center_stats_url(self.test_center.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify statistics structure
        expected_fields = ['total_samples', 'pending_samples', 'processing_samples', 
                          'completed_samples', 'rejected_samples', 'archived_samples']
        self.assert_required_fields(data, expected_fields)
        
        # Verify all values are integers
        for field in expected_fields:
            self.assertIsInstance(data[field], int)
    
    def test_centers_summary(self):
        """Test centers summary endpoint."""
        self.authenticate_admin()
        
        response = self.client.get(self.center_summary_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify summary structure
        expected_fields = ['total_centers', 'active_centers', 'inactive_centers']
        self.assert_required_fields(data, expected_fields)
        
        # Verify values
        self.assertIsInstance(data['total_centers'], int)
        self.assertIsInstance(data['active_centers'], int)
        self.assertIsInstance(data['inactive_centers'], int)
        self.assertGreaterEqual(data['total_centers'], 2)  # At least our test centers
    
    def test_centers_ordering(self):
        """Test centers list ordering."""
        self.authenticate_admin()
        
        # Test ordering by name
        response = self.client.get(self.centers_url, {'ordering': 'name'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        names = [c['name'] for c in data['results']]
        self.assertEqual(names, sorted(names))
        
        # Test reverse ordering
        response = self.client.get(self.centers_url, {'ordering': '-name'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        names = [c['name'] for c in data['results']]
        self.assertEqual(names, sorted(names, reverse=True))
    
    def test_centers_security_sql_injection(self):
        """Test SQL injection protection in centers endpoints."""
        self.authenticate_admin()
        
        # Test SQL injection in search parameter
        self.test_sql_injection(self.centers_url, {'search': 'test'})
        
        # Test SQL injection in filter parameters
        self.test_sql_injection(self.centers_url, {'is_active': 'true'})
    
    def test_centers_security_xss(self):
        """Test XSS protection in centers endpoints."""
        self.authenticate_admin()
        
        # Test XSS in center creation
        center_data = TestDataFactory.center_data(
            name='XSS Test Center',
            code='XSS001',
            address='XSS Test Address'
        )
        
        self.test_xss_protection(self.centers_url, center_data)
    
    def test_centers_performance_query_count(self):
        """Test database query performance for centers list."""
        self.authenticate_admin()
        
        # Test query count for centers list
        with self.assert_query_count(3):  # Expected: user auth, centers query, count query
            response = self.client.get(self.centers_url)
            self.assertResponseSuccess(response)
    
    def test_centers_performance_response_time(self):
        """Test response time performance for centers list."""
        self.authenticate_admin()
        
        # Create more centers for performance testing
        for i in range(50):
            self.create_test_center(
                name=f'Performance Test Center {i}',
                code=f'PTC{i:03d}',
                address=f'Performance Address {i}'
            )
        
        # Test response time
        def make_request():
            return self.client.get(self.centers_url)
        
        response = self.measure_response_time(make_request, max_time_ms=2000)
        self.assertResponseSuccess(response)
    
    @override_settings(DEBUG=True)
    def test_centers_debug_mode_security(self):
        """Test that debug information is not exposed in production-like scenarios."""
        self.authenticate_admin()
        
        # Try to cause an error and verify debug info is not exposed
        invalid_url = self.center_detail_url('invalid-uuid')
        response = self.client.get(invalid_url)
        
        # Should get 404, not 500 with debug info
        self.assertResponseError(response, status.HTTP_404_NOT_FOUND)
        
        response_content = response.content.decode()
        self.assertNotIn('Traceback', response_content)
        self.assertNotIn('Django', response_content)
    
    def test_centers_concurrent_access(self):
        """Test concurrent access to centers endpoints."""
        import threading
        import time
        
        self.authenticate_admin()
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = self.client.get(self.centers_url)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads for concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        self.assertEqual(len(results), 5)
        for status_code in results:
            self.assertEqual(status_code, 200)
    
    def test_centers_field_validation_edge_cases(self):
        """Test edge cases for field validation."""
        self.authenticate_admin()
        
        # Test extremely long name
        long_name_data = TestDataFactory.center_data(
            name='A' * 300,  # Assuming max_length is 255
            code='LONG001',
            address='Long Name Address'
        )
        
        response = self.client.post(self.centers_url, long_name_data, format='json')
        self.assertResponseError(response)
        
        # Test empty strings
        empty_data = TestDataFactory.center_data(
            name='',
            code='EMPTY001',
            address='Empty Name Address'
        )
        
        response = self.client.post(self.centers_url, empty_data, format='json')
        self.assertResponseError(response)
        
        # Test special characters in code
        special_char_data = TestDataFactory.center_data(
            name='Special Char Center',
            code='SC@#$%',
            address='Special Char Address'
        )
        
        response = self.client.post(self.centers_url, special_char_data, format='json')
        # This might succeed or fail depending on validation rules
        # The test documents the current behavior
        self.assertIn(response.status_code, [201, 400])
    
    def test_centers_audit_trail(self):
        """Test audit trail functionality for centers."""
        self.authenticate_admin()
        
        # Create center
        center_data = TestDataFactory.center_data(
            name='Audit Test Center',
            code='ATC001',
            address='Audit Test Address'
        )
        
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        data = self.get_response_data(response)
        center_id = data['id']
        
        # Verify created_at and updated_at are set
        self.assert_timestamp_field(data, 'created_at')
        self.assert_timestamp_field(data, 'updated_at')
        
        # Update center and verify updated_at changes
        original_updated_at = data['updated_at']
        
        # Wait a moment to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        update_data = {'name': 'Updated Audit Test Center'}
        url = self.center_detail_url(center_id)
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        updated_data = self.get_response_data(response)
        self.assertNotEqual(updated_data['updated_at'], original_updated_at)
        self.assertEqual(updated_data['created_at'], data['created_at'])  # Should not change 

    def test_center_permissions(self):
        """Test center endpoint permissions."""
        center_data = TestDataFactory.center_data(
            name='Permission Test Center',
            code='PTC001',
            address='Permission Test Address'
        )
        
        # Test unauthenticated user
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test regular user (should be forbidden)
        self.authenticate_regular_user()
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.post(self.centers_url, center_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED) 