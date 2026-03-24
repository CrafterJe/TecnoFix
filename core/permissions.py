from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Solo administradores."""
    message = 'Se requiere rol de Administrador.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == 'admin'
        )


class IsTecnico(BasePermission):
    """Solo técnicos."""
    message = 'Se requiere rol de Técnico.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == 'tecnico'
        )


class IsRecepcion(BasePermission):
    """Solo recepción."""
    message = 'Se requiere rol de Recepción.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == 'recepcion'
        )


class IsAdminOrTecnico(BasePermission):
    """Administradores o técnicos."""
    message = 'Se requiere rol de Administrador o Técnico.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol in ('admin', 'tecnico')
        )


class IsAdminOrReadOnly(BasePermission):
    """Lectura para todos autenticados, escritura solo para admin."""
    message = 'Se requiere rol de Administrador para modificar.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.rol == 'admin'


class IsOwnerOrAdmin(BasePermission):
    """El propio usuario o un administrador."""
    message = 'Solo puedes acceder a tus propios recursos.'

    def has_object_permission(self, request, view, obj):
        if request.user.rol == 'admin':
            return True
        return obj == request.user or getattr(obj, 'created_by', None) == request.user
