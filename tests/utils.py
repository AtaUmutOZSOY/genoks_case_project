"""
Test utilities for multi-tenant Django application.
Provides base test classes, fixtures, and helper functions for comprehensive API testing.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.centers.models import Center
from apps.users.models import User
from utils.tenant_utils import create_tenant_schema, delete_tenant_schema, set_tenant_schema


User = get_user_model()


class MultiTenantTestMixin:
    """Mixin for multi-tenant test functionality."""
    
    def setUp(self):
        super().setUp()
        self.tenant_schemas = []
    
    def tearDown(self):
        """Clean up tenant schemas after tests."""
        for schema_name in self.tenant_schemas:
            try:
                delete_tenant_schema(schema_name)
            except Exception:
                pass  # Schema might not exist
        super().tearDown()
    
    def create_test_tenant_schema(self, schema_name: str) -> str:
        """Create a test tenant schema and track it for cleanup."""
        create_tenant_schema(schema_name)
        self.tenant_schemas.append(schema_name)
        return schema_name


class BaseAPITestCase(APITestCase, MultiTenantTestMixin):
    """Base test case for API testing with common setup and utilities."""
    
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.maxDiff = None  # Show full diff in test failures
        
        # Create test users with different roles
        self.admin_user = self.create_test_user(
            username='admin_user',
            email='admin@test.com',
            role='admin'
        )
        self.regular_user = self.create_test_user(
            username='regular_user',
            email='user@test.com',
            role='user'
        )
        self.viewer_user = self.create_test_user(
            username='viewer_user',
            email='viewer@test.com',
            role='viewer'
        )
        
        # Create test centers
        self.test_center = self.create_test_center(
            name='Test Center',
            code='TC001',
            address='Test Address'
        )
        self.another_center = self.create_test_center(
            name='Another Center',
            code='AC002',
            address='Another Address'
        )
        
        # Assign users to centers
        self.admin_user.center = self.test_center
        self.admin_user.save()
        self.regular_user.center = self.test_center
        self.regular_user.save()
        self.viewer_user.center = self.another_center
        self.viewer_user.save()
    
    def create_test_user(self, username: str, email: str, role: str = 'user', 
                        center: Optional[Center] = None) -> User:
        """Create a test user with specified role."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=role,
            center=center
        )
        return user
    
    def create_test_center(self, name: str, code: str, address: str, 
                          is_active: bool = True) -> Center:
        """Create a test center."""
        center = Center.objects.create(
            name=name,
            code=code,
            address=address,
            phone='123-456-7890',
            email=f'{code.lower()}@test.com',
            is_active=is_active
        )
        return center
    
    def authenticate_user(self, user: User):
        """Authenticate a user for API requests."""
        self.client.force_authenticate(user=user)
    
    def authenticate_admin(self):
        """Authenticate admin user."""
        self.authenticate_user(self.admin_user)
    
    def authenticate_regular_user(self):
        """Authenticate regular user."""
        self.authenticate_user(self.regular_user)
    
    def authenticate_viewer(self):
        """Authenticate viewer user."""
        self.authenticate_user(self.viewer_user)
    
    def logout(self):
        """Logout current user."""
        self.client.force_authenticate(user=None)
    
    def assertResponseSuccess(self, response, expected_status=status.HTTP_200_OK):
        """Assert response is successful with expected status."""
        self.assertEqual(response.status_code, expected_status,
                        f"Expected {expected_status}, got {response.status_code}. "
                        f"Response: {response.content.decode()}")
    
    def assertResponseError(self, response, expected_status=status.HTTP_400_BAD_REQUEST):
        """Assert response is an error with expected status."""
        self.assertEqual(response.status_code, expected_status,
                        f"Expected {expected_status}, got {response.status_code}. "
                        f"Response: {response.content.decode()}")
    
    def assertResponseForbidden(self, response):
        """Assert response is forbidden."""
        self.assertResponseError(response, status.HTTP_403_FORBIDDEN)
    
    def assertResponseUnauthorized(self, response):
        """Assert response is unauthorized."""
        self.assertResponseError(response, status.HTTP_401_UNAUTHORIZED)
    
    def assertResponseNotFound(self, response):
        """Assert response is not found."""
        self.assertResponseError(response, status.HTTP_404_NOT_FOUND)
    
    def get_response_data(self, response) -> Dict[Any, Any]:
        """Get response data as dictionary."""
        return json.loads(response.content.decode())
    
    def assert_pagination_response(self, response_data: Dict[Any, Any]):
        """Assert response has pagination structure."""
        self.assertIn('count', response_data)
        self.assertIn('next', response_data)
        self.assertIn('previous', response_data)
        self.assertIn('results', response_data)
        self.assertIsInstance(response_data['results'], list)
    
    def assert_uuid_field(self, data: Dict[Any, Any], field_name: str):
        """Assert field is a valid UUID."""
        self.assertIn(field_name, data)
        try:
            uuid.UUID(data[field_name])
        except (ValueError, TypeError):
            self.fail(f"Field '{field_name}' is not a valid UUID: {data[field_name]}")
    
    def assert_timestamp_field(self, data: Dict[Any, Any], field_name: str):
        """Assert field is a valid timestamp."""
        self.assertIn(field_name, data)
        try:
            datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            self.fail(f"Field '{field_name}' is not a valid timestamp: {data[field_name]}")
    
    def assert_required_fields(self, data: Dict[Any, Any], required_fields: List[str]):
        """Assert all required fields are present in data."""
        for field in required_fields:
            self.assertIn(field, data, f"Required field '{field}' missing from response")
    
    def create_test_payload(self, **kwargs) -> Dict[str, Any]:
        """Create a test payload with default values that can be overridden."""
        return kwargs


class TenantAwareTestCase(BaseAPITestCase):
    """Test case for tenant-aware functionality."""
    
    def setUp(self):
        super().setUp()
        # Create tenant schemas for test centers
        self.test_center_schema = f"center_{self.test_center.id.hex}"
        self.another_center_schema = f"center_{self.another_center.id.hex}"
        
        self.create_test_tenant_schema(self.test_center_schema)
        self.create_test_tenant_schema(self.another_center_schema)
    
    def with_tenant_context(self, center: Center):
        """Context manager for tenant operations."""
        return set_tenant_schema(f"center_{center.id.hex}")


class MockTimeTestMixin:
    """Mixin for mocking time in tests."""
    
    def mock_now(self, mock_datetime: datetime):
        """Mock datetime.now() to return specific datetime."""
        return patch('django.utils.timezone.now', return_value=mock_datetime)


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def center_data(**kwargs) -> Dict[str, Any]:
        """Generate center test data."""
        defaults = {
            'name': 'Test Center',
            'code': 'TC001',
            'address': '123 Test Street',
            'phone': '123-456-7890',
            'email': 'test@center.com',
            'is_active': True
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def user_data(**kwargs) -> Dict[str, Any]:
        """Generate user test data."""
        defaults = {
            'username': 'testuser',
            'email': 'test@user.com',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'user',
            'is_active': True
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def sample_data(**kwargs) -> Dict[str, Any]:
        """Generate sample test data."""
        defaults = {
            'patient_name': 'Test Patient',
            'patient_id': 'P12345',
            'sample_type': 'blood',
            'priority': 'normal',
            'notes': 'Test sample notes'
        }
        defaults.update(kwargs)
        return defaults


# Performance testing utilities
class PerformanceTestMixin:
    """Mixin for performance testing."""
    
    def assert_query_count(self, expected_count: int):
        """Assert database query count."""
        return self.assertNumQueries(expected_count)
    
    def measure_response_time(self, func, max_time_ms: int = 1000):
        """Measure and assert response time."""
        import time
        start_time = time.time()
        result = func()
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        self.assertLess(response_time_ms, max_time_ms,
                       f"Response time {response_time_ms:.2f}ms exceeds maximum {max_time_ms}ms")
        return result


# Security testing utilities
class SecurityTestMixin:
    """Mixin for security testing."""
    
    def test_sql_injection(self, url: str, params: Dict[str, str]):
        """Test for SQL injection vulnerabilities."""
        sql_payloads = [
            "'; DROP TABLE centers; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --",
            "' UNION SELECT NULL,NULL,NULL--"
        ]
        
        for payload in sql_payloads:
            for param_name in params:
                test_params = params.copy()
                test_params[param_name] = payload
                
                response = self.client.get(url, test_params)
                # Should not return 500 (server error) or expose database errors
                self.assertNotEqual(response.status_code, 500,
                                  f"SQL injection payload caused server error: {payload}")
    
    def test_xss_protection(self, url: str, data: Dict[str, Any]):
        """Test for XSS protection."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            for field_name in data:
                test_data = data.copy()
                test_data[field_name] = payload
                
                response = self.client.post(url, test_data, format='json')
                # Response should not contain unescaped payload
                response_content = response.content.decode()
                self.assertNotIn(payload, response_content,
                               f"XSS payload not properly escaped: {payload}")


# API documentation testing
class APIDocumentationTestMixin:
    """Mixin for API documentation testing."""
    
    def assert_openapi_schema_compliance(self, response, expected_schema: Dict[str, Any]):
        """Assert response complies with OpenAPI schema."""
        # This would integrate with tools like jsonschema for validation
        # For now, we'll do basic structure validation
        response_data = self.get_response_data(response)
        
        if 'properties' in expected_schema:
            for prop_name, prop_schema in expected_schema['properties'].items():
                if prop_schema.get('required', False):
                    self.assertIn(prop_name, response_data,
                                f"Required property '{prop_name}' missing from response") 