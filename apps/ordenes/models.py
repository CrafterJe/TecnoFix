from django.conf import settings
from django.db import models

from core.mixins import AuditableMixin
from core.models import BaseModel


def evidencia_upload_path(instance, filename):
    return f'evidencias/orden_{instance.orden.numero_orden}/{filename}'


class Orden(AuditableMixin, BaseModel):
    ESTADO_CHOICES = [
        ('recibido', 'Recibido'),
        ('diagnostico', 'En diagnóstico'),
        ('esperando_refaccion', 'Esperando refacción'),
        ('en_reparacion', 'En reparación'),
        ('listo', 'Listo para entregar'),
        ('entregado', 'Entregado'),
    ]

    numero_orden = models.CharField('Número de orden', max_length=25, unique=True, blank=True)
    dispositivo = models.ForeignKey(
        'clientes.Dispositivo',
        on_delete=models.PROTECT,
        related_name='ordenes',
        verbose_name='Dispositivo',
    )
    problema_reportado = models.TextField('Problema reportado')
    diagnostico = models.TextField('Diagnóstico', blank=True)
    estado = models.CharField('Estado', max_length=25, choices=ESTADO_CHOICES, default='recibido')
    costo_estimado = models.DecimalField('Costo estimado', max_digits=10, decimal_places=2, null=True, blank=True)
    costo_final = models.DecimalField('Costo final', max_digits=10, decimal_places=2, null=True, blank=True)

    # Usuarios relacionados
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='ordenes_creadas', verbose_name='Registrado por',
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordenes_recibidas', verbose_name='Recibido físicamente por',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordenes_asignadas', verbose_name='Técnico asignado',
    )
    delivered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordenes_entregadas', verbose_name='Entregado por',
    )
    status_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordenes_estado_actualizado', verbose_name='Último cambio de estado por',
    )

    class Meta:
        db_table = 'ordenes'
        verbose_name = 'Orden de servicio'
        verbose_name_plural = 'Órdenes de servicio'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.numero_orden} — {self.dispositivo}'

    def save(self, *args, **kwargs):
        if not self.numero_orden:
            from core.utils import generate_order_number
            self.numero_orden = generate_order_number()
        super().save(*args, **kwargs)


class Evidencia(AuditableMixin, BaseModel):
    TIPO_CHOICES = [
        ('recepcion', 'Recepción'),
        ('proceso', 'En proceso'),
        ('entrega', 'Entrega'),
    ]

    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='evidencias',
        verbose_name='Orden',
    )
    imagen = models.ImageField('Imagen', upload_to=evidencia_upload_path)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='evidencias_subidas',
        verbose_name='Subido por',
    )

    class Meta:
        db_table = 'evidencias'
        verbose_name = 'Evidencia'
        verbose_name_plural = 'Evidencias'
        ordering = ['-created_at']

    def __str__(self):
        return f'Evidencia {self.get_tipo_display()} — {self.orden.numero_orden}'


class OrdenRefaccion(AuditableMixin, BaseModel):
    """Refacciones usadas en una orden de servicio."""
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='refacciones_usadas',
        verbose_name='Orden',
    )
    refaccion = models.ForeignKey(
        'inventario.Refaccion',
        on_delete=models.PROTECT,
        related_name='usos_en_ordenes',
        verbose_name='Refacción',
    )
    cantidad = models.PositiveIntegerField('Cantidad', default=1)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='refacciones_agregadas',
        verbose_name='Agregado por',
    )

    class Meta:
        db_table = 'ordenes_refacciones'
        verbose_name = 'Refacción en orden'
        verbose_name_plural = 'Refacciones en orden'

    def __str__(self):
        return f'{self.refaccion.nombre} x{self.cantidad} — {self.orden.numero_orden}'
