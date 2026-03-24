from django.conf import settings
from django.db import models

from core.mixins import AuditableMixin
from core.models import BaseModel


class Cliente(AuditableMixin, BaseModel):
    nombre = models.CharField('Nombre', max_length=150)
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    email = models.EmailField('Correo electrónico', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clientes_creados',
        verbose_name='Registrado por',
    )

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Dispositivo(AuditableMixin, BaseModel):
    TIPO_CHOICES = [
        ('celular', 'Celular'),
        ('tablet', 'Tablet'),
        ('laptop', 'Laptop'),
        ('computadora', 'Computadora'),
        ('otro', 'Otro'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='dispositivos',
        verbose_name='Cliente',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField('Marca', max_length=100)
    modelo = models.CharField('Modelo', max_length=100)

    class Meta:
        db_table = 'dispositivos'
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'
        ordering = ['marca', 'modelo']

    def __str__(self):
        return f'{self.marca} {self.modelo} ({self.get_tipo_display()}) — {self.cliente}'
