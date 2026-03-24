from django.contrib import admin

from .models import Refaccion, RefaccionCompatible


class RefaccionCompatibleInline(admin.TabularInline):
    model = RefaccionCompatible
    extra = 0


@admin.register(Refaccion)
class RefaccionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'stock', 'stock_minimo', 'precio_venta']
    list_filter = ['categoria']
    search_fields = ['nombre', 'descripcion']
    inlines = [RefaccionCompatibleInline]


@admin.register(RefaccionCompatible)
class RefaccionCompatibleAdmin(admin.ModelAdmin):
    list_display = ['refaccion', 'marca', 'modelo', 'tipo_dispositivo']
    search_fields = ['marca', 'modelo', 'refaccion__nombre']
