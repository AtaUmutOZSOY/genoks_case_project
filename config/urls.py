"""
URL Configuration for multi-tenant Django project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView, 
    SpectacularSwaggerView
)

# Customize admin site
admin.site.site_header = "Multi-tenant System Administration"
admin.site.site_title = "Multi-tenant Admin"
admin.site.index_title = "Welcome to Multi-tenant Administration"

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API endpoints
    path('api/', include('apps.centers.urls')),
    path('api/', include('apps.users.urls')),
    path('api/centers/<uuid:center_id>/', include('apps.samples.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 