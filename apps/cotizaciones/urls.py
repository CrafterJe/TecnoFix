from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApiProductoCatalogoViewSet,
    CategoriaDispositivoViewSet,
    CotizacionViewSet,
    FormulaReparacionViewSet,
    FuenteApiViewSet,
    ResolverFormulaView,
    SubcategoriaDispositivoViewSet,
    TipoReparacionViewSet,
)

router = DefaultRouter()
router.register('categorias', CategoriaDispositivoViewSet, basename='cotizacion-categoria')
router.register('subcategorias', SubcategoriaDispositivoViewSet, basename='cotizacion-subcategoria')
router.register('tipos-reparacion', TipoReparacionViewSet, basename='cotizacion-tipo-reparacion')
router.register('formulas', FormulaReparacionViewSet, basename='cotizacion-formula')
router.register('fuentes-api', FuenteApiViewSet, basename='cotizacion-fuente-api')
router.register('productos-api', ApiProductoCatalogoViewSet, basename='cotizacion-producto-api')
router.register('resolver-formula', ResolverFormulaView, basename='cotizacion-resolver-formula')
router.register('', CotizacionViewSet, basename='cotizacion')

urlpatterns = [
    path('', include(router.urls)),
]
