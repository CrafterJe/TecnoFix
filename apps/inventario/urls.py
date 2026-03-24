from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RefaccionCompatibleViewSet, RefaccionViewSet

router = DefaultRouter()
router.register('compatibilidades', RefaccionCompatibleViewSet, basename='refaccion-compatible')
router.register('', RefaccionViewSet, basename='refaccion')

urlpatterns = [
    path('', include(router.urls)),
]
