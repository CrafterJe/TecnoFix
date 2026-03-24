from django.contrib import admin

from .models import Cliente, Dispositivo


class DispositivoInline(admin.TabularInline):
    model = Dispositivo
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'telefono', 'email', 'created_by', 'created_at']
    search_fields = ['nombre', 'telefono', 'email']
    inlines = [DispositivoInline]


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ['marca', 'modelo', 'tipo', 'cliente']
    list_filter = ['tipo', 'marca']
    search_fields = ['marca', 'modelo', 'cliente__nombre']
