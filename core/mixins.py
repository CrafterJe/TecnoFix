class AuditableMixin:
    """
    Mixin marcador para indicar que un modelo debe ser registrado en AuditLog.
    No hereda de models.Model — es un marcador puro para evitar conflictos de MRO.

    Uso:
        class MiModelo(AuditableMixin, models.Model):
            ...
    """
    pass
