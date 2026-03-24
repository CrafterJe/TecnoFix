from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EvidenciaViewSet, OrdenViewSet

router = DefaultRouter()
router.register('evidencias', EvidenciaViewSet, basename='evidencia')
router.register('', OrdenViewSet, basename='orden')

urlpatterns = [
    path('', include(router.urls)),
]
