import threading

_thread_locals = threading.local()


def get_current_user():
    """Retorna el usuario autenticado del request actual (thread-local)."""
    return getattr(_thread_locals, 'user', None)


def get_current_ip():
    """Retorna la IP del request actual (thread-local)."""
    return getattr(_thread_locals, 'ip_address', None)


class AuditMiddleware:
    """
    Almacena el usuario actual y su IP en thread-local para ser usados
    por los signals de auditoría sin necesidad de pasar el request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = request.user if request.user.is_authenticated else None
        _thread_locals.ip_address = self._get_client_ip(request)

        response = self.get_response(request)

        # Limpiar al terminar el request
        _thread_locals.user = None
        _thread_locals.ip_address = None

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
