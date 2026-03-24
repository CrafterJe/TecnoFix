from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from core.mixins import AuditableMixin


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es requerido.')
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('activo', True)
        return self.create_user(email, nombre, password, **extra_fields)


class Usuario(AuditableMixin, AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('tecnico', 'Técnico'),
        ('recepcion', 'Recepción'),
    ]

    nombre = models.CharField('Nombre completo', max_length=150)
    email = models.EmailField('Correo electrónico', unique=True)
    rol = models.CharField('Rol', max_length=20, choices=ROL_CHOICES, default='recepcion')
    activo = models.BooleanField('Activo', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    fecha_creacion = models.DateTimeField('Fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_rol_display()})'

    @property
    def is_active(self):
        return self.activo

    @property
    def is_admin(self):
        return self.rol == 'admin'

    @property
    def is_tecnico(self):
        return self.rol == 'tecnico'

    @property
    def is_recepcion(self):
        return self.rol == 'recepcion'
