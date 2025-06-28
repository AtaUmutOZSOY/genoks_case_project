"""
Comprehensive tests for Centers API endpoints.
Tests all CRUD operations, custom actions, filtering, pagination, and permissions.
"""

import uuid
from django.urls import reverse
from rest_framework import status
from tests.utils import BaseAPITestCase


class CentersAPITestCase(BaseAPITestCase):
    """Test cases for Centers API endpoints."""

    def setUp(self):
        super().setUp()
        self.centers_url = reverse('center-list')
        self.center_detail_url = lambda pk: reverse('center-detail', kwargs={'pk': pk})
        self.center_stats_url = lambda pk: reverse('center-stats', kwargs={'pk': pk})
        self.center_summary_url = reverse('center-summary')
        self.center_restore_url = lambda pk: reverse('center-restore', kwargs={'pk': pk})

    def test_list_centers_unauthenticated(self):
        """Test that unauthenticated users cannot access centers list."""
        response = self.client.get(self.centers_url)
        self.assertResponseForbidden(response)

    def test_list_centers_authenticated(self):
        """Test authenticated users can list centers."""
        self.authenticate_admin()
        response = self.client.get(self.centers_url)
        self.assertResponseSuccess(response)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)

    def test_list_centers_pagination(self):
        """Test centers list pagination."""
        for i in range(15):
            self.create_test_center(
                name=f'Pagination Test Center {i}',
                schema_name=f'center_pagination_{i}',
                description=f'Pagination test description {i}'
            )

        self.authenticate_admin()
        
        response = self.client.get(self.centers_url)
        self.assertResponseSuccess(response)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
        self.assertGreaterEqual(response.data['count'], 15)

    def test_list_centers_ordering(self):
        """Test centers list ordering."""
        self.authenticate_admin()
        
        response = self.client.get(self.centers_url, {'ordering': 'name'})
        self.assertResponseSuccess(response)
        
        response = self.client.get(self.centers_url, {'ordering': '-created_at'})
        self.assertResponseSuccess(response)

    def test_list_centers_filtering(self):
        """Test centers list filtering."""
        active_center = self.create_test_center(
            name='Active Center',
            description='Active center for testing'
        )
        inactive_center = self.create_test_center(
            name='Inactive Center',
            description='Inactive center for testing'
        )
        inactive_center.soft_delete()

        self.authenticate_admin()
        
        response = self.client.get(self.centers_url)
        self.assertResponseSuccess(response)
        center_names = [center['name'] for center in response.data['results']]
        self.assertIn('Active Center', center_names)
        self.assertNotIn('Inactive Center', center_names)
        
        response = self.client.get(self.centers_url, {'include_inactive': 'true'})
        self.assertResponseSuccess(response)
        center_names = [center['name'] for center in response.data['results']]
        self.assertIn('Active Center', center_names)
        self.assertIn('Inactive Center', center_names)

    def test_list_centers_search(self):
        """Test centers list search functionality."""
        search_center = self.create_test_center(
            name='Unique Search Center',
            schema_name='center_search_unique',
            description='Unique center for search testing'
        )

        self.authenticate_admin()
        
        # Test search by name
        response = self.client.get(self.centers_url, {'search': 'Unique Search'})
        self.assertResponseSuccess(response)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Unique Search Center')
        
        # Test search by description
        response = self.client.get(self.centers_url, {'search': 'search testing'})
        self.assertResponseSuccess(response)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_center_authenticated(self):
        """Test authenticated users can create centers."""
        self.authenticate_admin()
        
        center_data = {
            'name': 'New Test Center',
            'description': 'A new center for testing'
        }
        
        response = self.client.post(self.centers_url, center_data)
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], center_data['name'])
        self.assertIn('schema_name', response.data['data'])
        self.assertTrue(response.data['data']['schema_name'].startswith('center_'))

    def test_create_center_unauthenticated(self):
        """Test unauthenticated users cannot create centers."""
        center_data = {
            'name': 'Unauthorized Center',
            'schema_name': 'center_unauthorized',
            'description': 'Should not be created'
        }
        
        response = self.client.post(self.centers_url, center_data)
        self.assertResponseForbidden(response)

    def test_create_center_validation(self):
        """Test center creation validation."""
        self.authenticate_admin()
        
        response = self.client.post(self.centers_url, {})
        self.assertResponseError(response, status.HTTP_400_BAD_REQUEST)
        
        invalid_data = {
            'name': '',
            'description': 'Should fail due to empty name'
        }
        
        response = self.client.post(self.centers_url, invalid_data)
        self.assertResponseError(response, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_center_authenticated(self):
        """Test authenticated users can retrieve center details."""
        self.authenticate_admin()
        
        response = self.client.get(self.center_detail_url(self.test_center.id))
        self.assertResponseSuccess(response)
        self.assertEqual(response.data['id'], str(self.test_center.id))
        self.assertEqual(response.data['name'], self.test_center.name)

    def test_retrieve_center_unauthenticated(self):
        """Test unauthenticated users cannot retrieve center details."""
        response = self.client.get(self.center_detail_url(self.test_center.id))
        self.assertResponseForbidden(response)

    def test_retrieve_nonexistent_center(self):
        """Test retrieving a non-existent center returns 404."""
        self.authenticate_admin()
        
        fake_id = uuid.uuid4()
        response = self.client.get(self.center_detail_url(fake_id))
        self.assertResponseNotFound(response)

    def test_update_center_authenticated(self):
        """Test authenticated users can update centers."""
        self.authenticate_admin()
        
        update_data = {
            'name': 'Updated Center Name',
            'description': 'Updated description'
        }
        
        response = self.client.patch(self.center_detail_url(self.test_center.id), update_data)
        self.assertResponseSuccess(response)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], update_data['name'])
        self.assertEqual(response.data['data']['description'], update_data['description'])

    def test_update_center_unauthenticated(self):
        """Test unauthenticated users cannot update centers."""
        update_data = {'name': 'Unauthorized Update'}
        
        response = self.client.patch(self.center_detail_url(self.test_center.id), update_data)
        self.assertResponseForbidden(response)

    def test_delete_center_authenticated(self):
        """Test authenticated users can soft delete centers."""
        self.authenticate_admin()
        
        delete_center = self.create_test_center(
            name='Center to Delete',
            description='This center will be deleted'
        )
        
        response = self.client.delete(self.center_detail_url(delete_center.id))
        self.assertResponseSuccess(response)
        self.assertIn('message', response.data)
        
        delete_center.refresh_from_db()
        self.assertFalse(delete_center.is_active)

    def test_delete_center_unauthenticated(self):
        """Test unauthenticated users cannot delete centers."""
        response = self.client.delete(self.center_detail_url(self.test_center.id))
        self.assertResponseForbidden(response)

    def test_center_stats_authenticated(self):
        """Test authenticated users can get center statistics."""
        self.authenticate_admin()
        
        response = self.client.get(self.center_stats_url(self.test_center.id))
        self.assertResponseSuccess(response)
        self.assertIn('user_count', response.data)
        self.assertIn('sample_count', response.data)
        self.assertIn('is_active', response.data)

    def test_center_stats_unauthenticated(self):
        """Test unauthenticated users cannot get center statistics."""
        response = self.client.get(self.center_stats_url(self.test_center.id))
        self.assertResponseForbidden(response)

    def test_centers_summary_authenticated(self):
        """Test authenticated users can get centers summary."""
        self.authenticate_admin()
        
        response = self.client.get(self.center_summary_url)
        self.assertResponseSuccess(response)
        self.assertIn('data', response.data)
        self.assertIn('total_centers', response.data['data'])
        self.assertIn('active_centers', response.data['data'])

    def test_centers_summary_unauthenticated(self):
        """Test unauthenticated users cannot get centers summary."""
        response = self.client.get(self.center_summary_url)
        self.assertResponseForbidden(response)

    def test_restore_center_authenticated(self):
        """Test authenticated users can restore soft deleted centers."""
        self.authenticate_admin()
        
        restore_center = self.create_test_center(
            name='Center to Restore',
            description='This center will be restored'
        )
        restore_center.soft_delete()
        
        restore_center.refresh_from_db()
        
        response = self.client.post(self.center_restore_url(restore_center.id))
        self.assertResponseSuccess(response)
        self.assertIn('message', response.data)
        
        restore_center.refresh_from_db()
        self.assertTrue(restore_center.is_active)

    def test_restore_center_unauthenticated(self):
        """Test unauthenticated users cannot restore centers."""
        response = self.client.post(self.center_restore_url(self.test_center.id))
        self.assertResponseForbidden(response)

    def test_invalid_uuid_parameter(self):
        """Test API handles invalid UUID parameters gracefully."""
        self.authenticate_admin()
        
        response = self.client.get('/api/centers/invalid-uuid/')
        self.assertResponseNotFound(response)

    def test_large_pagination_request(self):
        """Test API handles large pagination requests."""
        self.authenticate_admin()
        
        response = self.client.get(self.centers_url, {'page_size': 10000})
        self.assertResponseSuccess(response)

    def test_special_characters_in_search(self):
        """Test search with special characters."""
        self.authenticate_admin()
        
        response = self.client.get(self.centers_url, {'search': '@#$%^&*()'})
        self.assertResponseSuccess(response)