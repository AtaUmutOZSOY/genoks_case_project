"""
URL patterns for Centers app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CenterViewSet

# Create a router and register the CenterViewSet
router = DefaultRouter()
router.register(r'centers', CenterViewSet, basename='center')

urlpatterns = [
    path('', include(router.urls)),
] 