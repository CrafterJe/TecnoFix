import threading

_thread_locals = threading.local()


def get_current_user():
    """Retorna el usuario autenticado del request actual (thread-local).

    Se lee de forma lazy desde el request para que DRF ya haya procesado
    el JWT antes de que los signals consulten el usuario.
    """
    request = getattr(_thread_locals, 'request', None)
    if request is None:
        return None
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    return user


def get_current_ip():
    """Retorna la IP del request actual (thread-local)."""
    return getattr(_thread_locals, 'ip_address', None)


class AuditMiddleware:
    """
    Almacena el request y la IP en thread-local para los signals de auditoría.
    El usuario se lee de forma lazy para que DRF ya haya autenticado el JWT.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        _thread_locals.ip_address = self._get_client_ip(request)

        response = self.get_response(request)

        _thread_locals.request = None
        _thread_locals.ip_address = None

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
