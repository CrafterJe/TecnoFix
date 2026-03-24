from django.db import models


class BaseModel(models.Model):
    """
    Modelo base abstracto con timestamps.
    Heredar para tener created_at y updated_at automáticos.
    """
    created_at = models.DateTimeField('Creado en', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        abstract = True
