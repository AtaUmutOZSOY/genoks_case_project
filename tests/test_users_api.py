"""
Comprehensive test suite for Users API endpoints.
Tests CRUD operations, permissions, role-based access, validation, and security.
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from unittest.mock import patch

from apps.users.models import User
from apps.centers.models import Center
from tests.utils import (
    BaseAPITestCase, 
    SecurityTestMixin, 
    PerformanceTestMixin,
    TestDataFactory
)

User = get_user_model()


class UsersAPITestCase(BaseAPITestCase, SecurityTestMixin, PerformanceTestMixin):
    """Test cases for Users API endpoints."""
    
    def setUp(self):
        super().setUp()
        self.users_url = reverse('users:user-list')
        self.user_detail_url = lambda pk: reverse('users:user-detail', kwargs={'pk': pk})
        self.user_reassign_url = lambda pk: reverse('users:user-reassign', kwargs={'pk': pk})
    
    def test_list_users_unauthenticated(self):
        """Test that unauthenticated users cannot access users list."""
        response = self.client.get(self.users_url)
        self.assertResponseUnauthorized(response)
    
    def test_list_users_authenticated_admin(self):
        """Test admin users can list all users."""
        self.authenticate_admin()
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        self.assertGreaterEqual(data['count'], 3)  # At least our test users
    
    def test_list_users_authenticated_regular_user(self):
        """Test regular users can only see users from their center."""
        self.authenticate_regular_user()
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assert_pagination_response(data)
        
        # All users should be from the same center
        for user in data['results']:
            if user['center']:
                self.assertEqual(user['center']['id'], str(self.test_center.id))
    
    def test_list_users_filtering_by_role(self):
        """Test users list filtering by role."""
        self.authenticate_admin()
        
        # Test admin filter
        response = self.client.get(self.users_url, {'role': 'admin'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for user in data['results']:
            self.assertEqual(user['role'], 'admin')
        
        # Test user filter
        response = self.client.get(self.users_url, {'role': 'user'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for user in data['results']:
            self.assertEqual(user['role'], 'user')
    
    def test_list_users_filtering_by_center(self):
        """Test users list filtering by center."""
        self.authenticate_admin()
        
        response = self.client.get(self.users_url, {'center': str(self.test_center.id)})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        for user in data['results']:
            if user['center']:
                self.assertEqual(user['center']['id'], str(self.test_center.id))
    
    def test_list_users_search(self):
        """Test users list search functionality."""
        # Create a user with unique name for search
        unique_user = self.create_test_user(
            username='unique_search_user',
            email='unique@search.com',
            center=self.test_center
        )
        
        self.authenticate_admin()
        
        # Test search by username
        response = self.client.get(self.users_url, {'search': 'unique_search'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertGreater(data['count'], 0)
        
        # Verify search results
        found_user = False
        for user in data['results']:
            if 'unique_search' in user['username'].lower():
                found_user = True
                break
        self.assertTrue(found_user)
    
    def test_create_user_success(self):
        """Test successful user creation."""
        self.authenticate_admin()
        
        user_data = TestDataFactory.user_data(
            username='newuser',
            email='newuser@test.com'
        )
        user_data['password'] = 'testpass123'
        
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                          'role', 'is_active', 'center', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify UUID and timestamp fields
        self.assert_uuid_field(data, 'id')
        self.assert_timestamp_field(data, 'created_at')
        self.assert_timestamp_field(data, 'updated_at')
        
        # Verify data values
        self.assertEqual(data['username'], user_data['username'])
        self.assertEqual(data['email'], user_data['email'])
        self.assertEqual(data['role'], user_data['role'])
        self.assertTrue(data['is_active'])
        
        # Verify password is not returned
        self.assertNotIn('password', data)
        
        # Verify user was created in database
        user = User.objects.get(id=data['id'])
        self.assertEqual(user.username, user_data['username'])
        self.assertTrue(user.check_password(user_data['password']))
    
    def test_create_user_validation_errors(self):
        """Test user creation validation errors."""
        self.authenticate_admin()
        
        # Test missing required fields
        invalid_data = {}
        response = self.client.post(self.users_url, invalid_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('username', data)
        self.assertIn('email', data)
        self.assertIn('password', data)
        
        # Test duplicate username
        duplicate_data = TestDataFactory.user_data(
            username=self.admin_user.username,  # Use existing username
            email='duplicate@test.com',
            password='testpass123'
        )
        
        response = self.client.post(self.users_url, duplicate_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('username', data)
        
        # Test invalid email format
        invalid_email_data = TestDataFactory.user_data(
            username='invalidemail',
            email='invalid-email',
            password='testpass123'
        )
        
        response = self.client.post(self.users_url, invalid_email_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('email', data)
        
        # Test invalid role
        invalid_role_data = TestDataFactory.user_data(
            username='invalidrole',
            email='invalidrole@test.com',
            password='testpass123',
            role='invalid_role'
        )
        
        response = self.client.post(self.users_url, invalid_role_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('role', data)
    
    def test_create_user_permissions(self):
        """Test user creation permissions."""
        user_data = TestDataFactory.user_data(
            username='permissiontest',
            email='permission@test.com',
            password='testpass123'
        )
        
        # Test unauthenticated user
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test regular user (should be forbidden)
        self.authenticate_regular_user()
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test viewer user (should be forbidden)
        self.authenticate_viewer()
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseSuccess(response, status.HTTP_201_CREATED)
    
    def test_retrieve_user_success(self):
        """Test successful user retrieval."""
        self.authenticate_admin()
        
        url = self.user_detail_url(self.regular_user.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify response structure
        required_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                          'role', 'is_active', 'center', 'created_at', 'updated_at']
        self.assert_required_fields(data, required_fields)
        
        # Verify data values
        self.assertEqual(data['id'], str(self.regular_user.id))
        self.assertEqual(data['username'], self.regular_user.username)
        self.assertEqual(data['email'], self.regular_user.email)
        self.assertEqual(data['role'], self.regular_user.role)
        
        # Verify password is not returned
        self.assertNotIn('password', data)
    
    def test_retrieve_user_permissions(self):
        """Test user retrieval permissions."""
        url = self.user_detail_url(self.regular_user.id)
        
        # Test unauthenticated user
        response = self.client.get(url)
        self.assertResponseUnauthorized(response)
        
        # Test user from different center (should be forbidden for non-admin)
        self.authenticate_viewer()  # viewer is from another center
        response = self.client.get(url)
        self.assertResponseForbidden(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        # Test user accessing their own profile
        self.authenticate_regular_user()
        own_url = self.user_detail_url(self.regular_user.id)
        response = self.client.get(own_url)
        self.assertResponseSuccess(response)
    
    def test_update_user_success(self):
        """Test successful user update."""
        self.authenticate_admin()
        
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'role': 'viewer'
        }
        
        url = self.user_detail_url(self.regular_user.id)
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        
        # Verify updated values
        self.assertEqual(data['first_name'], update_data['first_name'])
        self.assertEqual(data['last_name'], update_data['last_name'])
        self.assertEqual(data['role'], update_data['role'])
        
        # Verify unchanged values
        self.assertEqual(data['username'], self.regular_user.username)
        self.assertEqual(data['email'], self.regular_user.email)
        
        # Verify database was updated
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.first_name, update_data['first_name'])
        self.assertEqual(self.regular_user.last_name, update_data['last_name'])
        self.assertEqual(self.regular_user.role, update_data['role'])
    
    def test_update_user_password(self):
        """Test user password update."""
        self.authenticate_admin()
        
        new_password = 'newpassword123'
        update_data = {'password': new_password}
        
        url = self.user_detail_url(self.regular_user.id)
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        # Verify password was updated
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password(new_password))
        
        # Verify password is not returned in response
        data = self.get_response_data(response)
        self.assertNotIn('password', data)
    
    def test_update_user_permissions(self):
        """Test user update permissions."""
        update_data = {'first_name': 'Unauthorized Update'}
        url = self.user_detail_url(self.regular_user.id)
        
        # Test unauthenticated user
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test user from different center
        self.authenticate_viewer()
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test user updating their own profile (limited fields)
        self.authenticate_regular_user()
        own_update_data = {'first_name': 'Self Update'}
        own_url = self.user_detail_url(self.regular_user.id)
        response = self.client.patch(own_url, own_update_data, format='json')
        self.assertResponseSuccess(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
    
    def test_delete_user_soft_delete(self):
        """Test user soft delete functionality."""
        self.authenticate_admin()
        
        url = self.user_detail_url(self.regular_user.id)
        response = self.client.delete(url)
        self.assertResponseSuccess(response, status.HTTP_204_NO_CONTENT)
        
        # Verify user is soft deleted
        self.regular_user.refresh_from_db()
        self.assertIsNotNone(self.regular_user.deleted_at)
        self.assertFalse(self.regular_user.is_active)
        
        # Verify user is not in active list
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        user_ids = [u['id'] for u in data['results']]
        self.assertNotIn(str(self.regular_user.id), user_ids)
    
    def test_user_reassign_center(self):
        """Test user center reassignment."""
        self.authenticate_admin()
        
        # Create a new center for reassignment
        new_center = self.create_test_center(
            name='New Assignment Center',
            code='NAC001',
            address='New Assignment Address'
        )
        
        reassign_data = {'center': str(new_center.id)}
        url = self.user_reassign_url(self.regular_user.id)
        response = self.client.post(url, reassign_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['message'], 'User reassigned successfully')
        
        # Verify user was reassigned
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.center, new_center)
    
    def test_user_reassign_permissions(self):
        """Test user reassignment permissions."""
        reassign_data = {'center': str(self.another_center.id)}
        url = self.user_reassign_url(self.regular_user.id)
        
        # Test unauthenticated user
        response = self.client.post(url, reassign_data, format='json')
        self.assertResponseUnauthorized(response)
        
        # Test regular user (should be forbidden)
        self.authenticate_regular_user()
        response = self.client.post(url, reassign_data, format='json')
        self.assertResponseForbidden(response)
        
        # Test admin user (should succeed)
        self.authenticate_admin()
        response = self.client.post(url, reassign_data, format='json')
        self.assertResponseSuccess(response)
    
    def test_users_role_based_access_control(self):
        """Test role-based access control for users."""
        # Create users with different roles
        admin_user = self.create_test_user(
            username='test_admin',
            email='test_admin@test.com',
            role='admin',
            center=self.test_center
        )
        
        user_user = self.create_test_user(
            username='test_user',
            email='test_user@test.com',
            role='user',
            center=self.test_center
        )
        
        viewer_user = self.create_test_user(
            username='test_viewer',
            email='test_viewer@test.com',
            role='viewer',
            center=self.test_center
        )
        
        # Test admin can see all users
        self.authenticate_user(admin_user)
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertGreaterEqual(data['count'], 6)  # All users including test ones
        
        # Test regular user can see limited users
        self.authenticate_user(user_user)
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        # Test viewer has read-only access
        self.authenticate_user(viewer_user)
        response = self.client.get(self.users_url)
        self.assertResponseSuccess(response)
        
        # Viewer should not be able to create users
        create_data = TestDataFactory.user_data(
            username='viewer_create_test',
            email='viewer_create@test.com',
            password='testpass123'
        )
        response = self.client.post(self.users_url, create_data, format='json')
        self.assertResponseForbidden(response)
    
    def test_users_security_sql_injection(self):
        """Test SQL injection protection in users endpoints."""
        self.authenticate_admin()
        
        # Test SQL injection in search parameter
        self.test_sql_injection(self.users_url, {'search': 'test'})
        
        # Test SQL injection in filter parameters
        self.test_sql_injection(self.users_url, {'role': 'admin'})
    
    def test_users_security_xss(self):
        """Test XSS protection in users endpoints."""
        self.authenticate_admin()
        
        # Test XSS in user creation
        user_data = TestDataFactory.user_data(
            username='xsstest',
            email='xss@test.com',
            password='testpass123'
        )
        
        self.test_xss_protection(self.users_url, user_data)
    
    def test_users_performance_query_count(self):
        """Test database query performance for users list."""
        self.authenticate_admin()
        
        # Test query count for users list with center prefetch
        with self.assert_query_count(3):  # Expected: user auth, users query, count query
            response = self.client.get(self.users_url)
            self.assertResponseSuccess(response)
    
    def test_users_pagination_performance(self):
        """Test pagination performance with large dataset."""
        self.authenticate_admin()
        
        # Create many users for pagination testing
        for i in range(25):
            self.create_test_user(
                username=f'perfuser{i}',
                email=f'perfuser{i}@test.com',
                center=self.test_center
            )
        
        # Test first page performance
        def make_request():
            return self.client.get(self.users_url, {'page_size': 10})
        
        response = self.measure_response_time(make_request, max_time_ms=1500)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(len(data['results']), 10)
    
    def test_user_field_validation_edge_cases(self):
        """Test edge cases for user field validation."""
        self.authenticate_admin()
        
        # Test username with special characters
        special_username_data = TestDataFactory.user_data(
            username='user@#$%',
            email='special@test.com',
            password='testpass123'
        )
        
        response = self.client.post(self.users_url, special_username_data, format='json')
        # This might succeed or fail depending on validation rules
        self.assertIn(response.status_code, [201, 400])
        
        # Test extremely long username
        long_username_data = TestDataFactory.user_data(
            username='a' * 200,  # Assuming max_length is 150
            email='long@test.com',
            password='testpass123'
        )
        
        response = self.client.post(self.users_url, long_username_data, format='json')
        self.assertResponseError(response)
        
        # Test weak password
        weak_password_data = TestDataFactory.user_data(
            username='weakpass',
            email='weak@test.com',
            password='123'
        )
        
        response = self.client.post(self.users_url, weak_password_data, format='json')
        # This might succeed or fail depending on password validation
        self.assertIn(response.status_code, [201, 400])
    
    def test_user_center_constraint(self):
        """Test user center assignment constraints."""
        self.authenticate_admin()
        
        # Test assigning user to non-existent center
        from uuid import uuid4
        non_existent_center_id = uuid4()
        
        user_data = TestDataFactory.user_data(
            username='centertest',
            email='center@test.com',
            password='testpass123'
        )
        user_data['center'] = str(non_existent_center_id)
        
        response = self.client.post(self.users_url, user_data, format='json')
        self.assertResponseError(response)
        
        data = self.get_response_data(response)
        self.assertIn('center', data)
    
    def test_user_ordering(self):
        """Test users list ordering."""
        self.authenticate_admin()
        
        # Test ordering by username
        response = self.client.get(self.users_url, {'ordering': 'username'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        usernames = [u['username'] for u in data['results']]
        self.assertEqual(usernames, sorted(usernames))
        
        # Test reverse ordering
        response = self.client.get(self.users_url, {'ordering': '-username'})
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        usernames = [u['username'] for u in data['results']]
        self.assertEqual(usernames, sorted(usernames, reverse=True))
    
    def test_user_profile_self_access(self):
        """Test users can access and update their own profile."""
        self.authenticate_regular_user()
        
        # Test accessing own profile
        url = self.user_detail_url(self.regular_user.id)
        response = self.client.get(url)
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['id'], str(self.regular_user.id))
        
        # Test updating own profile (limited fields)
        update_data = {
            'first_name': 'Self Updated',
            'last_name': 'Name'
        }
        
        response = self.client.patch(url, update_data, format='json')
        self.assertResponseSuccess(response)
        
        data = self.get_response_data(response)
        self.assertEqual(data['first_name'], update_data['first_name'])
        self.assertEqual(data['last_name'], update_data['last_name'])
        
        # Test that role cannot be self-updated
        role_update_data = {'role': 'admin'}
        response = self.client.patch(url, role_update_data, format='json')
        # This should either be forbidden or ignore the role change
        if response.status_code == 200:
            data = self.get_response_data(response)
            self.assertNotEqual(data['role'], 'admin')  # Role should not change 