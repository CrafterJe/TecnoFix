from django.contrib import admin

from .models import (
    ApiProductoCatalogo,
    CategoriaDispositivo,
    Cotizacion,
    CotizacionItem,
    FormulaReparacion,
    FuenteApi,
    SubcategoriaDispositivo,
    TipoReparacion,
)


@admin.register(FuenteApi)
class FuenteApiAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'base_url', 'tipo_parser', 'activo', 'orden']
    list_filter = ['activo', 'tipo_parser']
    search_fields = ['nombre', 'slug', 'base_url']
    prepopulated_fields = {'slug': ('nombre',)}


class SubcategoriaInline(admin.TabularInline):
    model = SubcategoriaDispositivo
    extra = 0
    fields = ['nombre', 'slug', 'orden', 'activo']


class TipoReparacionInline(admin.TabularInline):
    model = TipoReparacion
    extra = 0
    fields = ['nombre', 'orden', 'activo']
    show_change_link = True


@admin.register(CategoriaDispositivo)
class CategoriaDispositivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'orden', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [SubcategoriaInline, TipoReparacionInline]


@admin.register(SubcategoriaDispositivo)
class SubcategoriaDispositivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'slug', 'orden', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre']
    prepopulated_fields = {'slug': ('nombre',)}


class FormulaReparacionInline(admin.TabularInline):
    model = FormulaReparacion
    extra = 0
    fields = ['subcategoria', 'es_personalizado', 'multiplicador', 'incremento', 'activo']


@admin.register(TipoReparacion)
class TipoReparacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'orden', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['nombre', 'descripcion']
    inlines = [FormulaReparacionInline]


@admin.register(FormulaReparacion)
class FormulaReparacionAdmin(admin.ModelAdmin):
    list_display = [
        'tipo_reparacion', 'subcategoria', 'es_personalizado',
        'multiplicador', 'incremento', 'activo',
    ]
    list_filter = ['tipo_reparacion__categoria', 'es_personalizado', 'activo']
    search_fields = ['tipo_reparacion__nombre']
    autocomplete_fields = ['tipo_reparacion', 'subcategoria']


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 0
    readonly_fields = ['precio_final', 'formula_snapshot', 'added_by', 'created_at']
    fields = [
        'tipo_reparacion', 'subcategoria', 'es_manual', 'fuente_api',
        'producto_titulo', 'precio_base', 'precio_final', 'es_personalizado',
        'cantidad', 'disponible', 'link_referencia', 'formula_snapshot', 'added_by',
    ]
    autocomplete_fields = ['fuente_api']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = [
        'numero_cotizacion', 'nombre_cliente', 'estado',
        'created_by', 'total_display', 'created_at',
    ]
    list_filter = ['estado', 'created_at']
    search_fields = ['numero_cotizacion', 'nombre_cliente']
    readonly_fields = ['numero_cotizacion', 'created_by', 'created_at', 'updated_at']
    autocomplete_fields = ['cliente']
    inlines = [CotizacionItemInline]

    @admin.display(description='Total')
    def total_display(self, obj):
        return f'${obj.total:.2f}'


@admin.register(CotizacionItem)
class CotizacionItemAdmin(admin.ModelAdmin):
    list_display = [
        'cotizacion', 'tipo_reparacion', 'subcategoria', 'origen_display',
        'precio_base', 'precio_final', 'cantidad', 'disponible',
    ]
    list_filter = ['es_manual', 'fuente_api', 'es_personalizado', 'disponible']
    search_fields = ['producto_titulo', 'cotizacion__numero_cotizacion']
    autocomplete_fields = ['cotizacion', 'tipo_reparacion', 'subcategoria', 'fuente_api']

    @admin.display(description='Origen')
    def origen_display(self, obj):
        if obj.es_manual:
            return 'Manual'
        return obj.fuente_api.nombre if obj.fuente_api else '—'


@admin.register(ApiProductoCatalogo)
class ApiProductoCatalogoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fuente', 'precio', 'disponible', 'synced_at']
    list_filter = ['fuente', 'disponible']
    search_fields = ['titulo', 'handle', 'vendor']
    autocomplete_fields = ['fuente']
    readonly_fields = ['synced_at']
