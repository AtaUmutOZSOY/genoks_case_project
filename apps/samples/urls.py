"""
URLs for the samples app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SampleViewSet

router = DefaultRouter()
router.register(r'samples', SampleViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 