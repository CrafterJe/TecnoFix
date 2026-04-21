from django.db import models

from core.mixins import AuditableMixin
from core.models import BaseModel


class Refaccion(AuditableMixin, BaseModel):
    nombre = models.CharField('Nombre', max_length=200)
    descripcion = models.TextField('Descripción', blank=True)
    categoria = models.CharField('Categoría', max_length=100, blank=True)
    stock = models.PositiveIntegerField('Stock actual', default=0)
    stock_minimo = models.PositiveIntegerField('Stock mínimo', default=1)
    precio_costo = models.DecimalField('Precio costo', max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField('Precio venta', max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'refacciones'
        verbose_name = 'Refacción'
        verbose_name_plural = 'Refacciones'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre'], name='idx_refacciones_nombre'),
            models.Index(fields=['categoria'], name='idx_refacciones_categoria'),
            models.Index(fields=['stock'], name='idx_refacciones_stock'),
        ]

    def __str__(self):
        return f'{self.nombre} (stock: {self.stock})'

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo


class RefaccionCompatible(AuditableMixin, BaseModel):
    """Compatibilidad de una refacción con marca/modelo/tipo de dispositivo."""
    refaccion = models.ForeignKey(
        Refaccion,
        on_delete=models.CASCADE,
        related_name='compatibilidades',
        verbose_name='Refacción',
    )
    marca = models.CharField('Marca', max_length=100)
    modelo = models.CharField('Modelo', max_length=100, blank=True)
    tipo_dispositivo = models.CharField('Tipo de dispositivo', max_length=50, blank=True)

    class Meta:
        db_table = 'refacciones_compatibles'
        verbose_name = 'Compatibilidad de refacción'
        verbose_name_plural = 'Compatibilidades de refacciones'
        indexes = [
            models.Index(fields=['marca'], name='idx_refcompat_marca'),
        ]

    def __str__(self):
        return f'{self.refaccion.nombre} → {self.marca} {self.modelo}'
