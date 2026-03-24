from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['email', 'nombre', 'rol', 'activo', 'fecha_creacion']
    list_filter = ['rol', 'activo']
    search_fields = ['email', 'nombre']
    ordering = ['nombre']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre',)}),
        ('Permisos', {'fields': ('rol', 'activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'rol', 'password1', 'password2'),
        }),
    )
