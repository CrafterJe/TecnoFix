from django.contrib import admin

from .models import Evidencia, Orden, OrdenRefaccion


class EvidenciaInline(admin.TabularInline):
    model = Evidencia
    extra = 0
    readonly_fields = ['uploaded_by', 'created_at']


class OrdenRefaccionInline(admin.TabularInline):
    model = OrdenRefaccion
    extra = 0
    readonly_fields = ['added_by']


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ['numero_orden', 'dispositivo', 'estado', 'assigned_to', 'created_at']
    list_filter = ['estado']
    search_fields = ['numero_orden', 'dispositivo__cliente__nombre', 'dispositivo__marca']
    readonly_fields = ['numero_orden', 'created_by', 'status_updated_by', 'created_at', 'updated_at']
    inlines = [EvidenciaInline, OrdenRefaccionInline]


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ['orden', 'tipo', 'uploaded_by', 'created_at']
    list_filter = ['tipo']
