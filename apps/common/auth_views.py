"""
Authentication views for API access.
"""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema
from django.contrib.auth.models import User


@extend_schema(
    summary="Login",
    description="Authenticate user and return API token for subsequent requests.",
    tags=["Authentication"],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string', 'description': 'Username'},
                'password': {'type': 'string', 'description': 'Password'}
            },
            'required': ['username', 'password']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'token': {'type': 'string', 'description': 'API Token'},
                'user_id': {'type': 'integer', 'description': 'User ID'},
                'username': {'type': 'string', 'description': 'Username'},
                'message': {'type': 'string', 'description': 'Success message'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'description': 'Error message'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login endpoint to obtain API token.
    
    Use the returned token in the Authorization header:
    Authorization: Token your-token-here
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        if user.is_active:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'message': 'Login successful'
            })
        else:
            return Response(
                {'error': 'User account is disabled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {'error': 'Invalid username or password'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Logout",
    description="Logout user and invalidate the current token.",
    tags=["Authentication"],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'}
            }
        },
        401: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'description': 'Authentication required'}
            }
        }
    }
)
@api_view(['POST'])
def logout_view(request):
    """
    Logout endpoint to invalidate current token.
    """
    try:
        # Delete the user's token to logout
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except (AttributeError, Token.DoesNotExist):
        return Response({'error': 'No active session found'}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
    tags=["Authentication"],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'user_id': {'type': 'integer', 'description': 'User ID'},
                'username': {'type': 'string', 'description': 'Username'},
                'email': {'type': 'string', 'description': 'Email'},
                'first_name': {'type': 'string', 'description': 'First name'},
                'last_name': {'type': 'string', 'description': 'Last name'},
                'is_staff': {'type': 'boolean', 'description': 'Is staff member'},
                'is_superuser': {'type': 'boolean', 'description': 'Is superuser'},
                'date_joined': {'type': 'string', 'description': 'Date joined'}
            }
        },
        401: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'description': 'Authentication required'}
            }
        }
    }
)
@api_view(['GET'])
def current_user_view(request):
    """
    Get current user information.
    """
    user = request.user
    return Response({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat()
    })


@extend_schema(
    summary="Create Superuser",
    description="Create a superuser account (for initial setup only).",
    tags=["Authentication"],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string', 'description': 'Username'},
                'password': {'type': 'string', 'description': 'Password'},
                'email': {'type': 'string', 'description': 'Email'}
            },
            'required': ['username', 'password', 'email']
        }
    },
    responses={
        201: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'Success message'},
                'user_id': {'type': 'integer', 'description': 'Created user ID'},
                'username': {'type': 'string', 'description': 'Username'}
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {'type': 'string', 'description': 'Error message'}
            }
        }
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_superuser_view(request):
    """
    Create superuser endpoint (for initial setup).
    
    Note: This endpoint should be disabled in production!
    """
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    
    if not all([username, password, email]):
        return Response(
            {'error': 'Username, password, and email are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        # Create token for immediate use
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'Superuser created successfully',
            'user_id': user.id,
            'username': user.username,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create user: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        ) 