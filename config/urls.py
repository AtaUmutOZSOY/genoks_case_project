"""
URL Configuration for multi-tenant Django project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView, 
    SpectacularSwaggerView
)
from apps.common.auth_views import (
    login_view,
    logout_view,
    current_user_view,
    create_superuser_view
)

# Customize admin site
admin.site.site_header = "Multi-tenant System Administration"
admin.site.site_title = "Multi-tenant Admin"
admin.site.index_title = "Welcome to Multi-tenant Administration"

urlpatterns = [
    # Root - Redirect to Swagger UI
    path('', lambda request: redirect('swagger-ui'), name='home'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication endpoints
    path('api/auth/login/', login_view, name='auth-login'),
    path('api/auth/logout/', logout_view, name='auth-logout'),
    path('api/auth/user/', current_user_view, name='auth-current-user'),
    path('api/auth/create-superuser/', create_superuser_view, name='auth-create-superuser'),
    
    # API endpoints
    path('api/', include('apps.centers.urls')),
    path('api/', include('apps.users.urls')),
    path('api/centers/<uuid:center_id>/', include('apps.samples.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 