"""
Middleware y utilidades de contexto de la aplicación 'operacion'.

El objetivo es que las señales de auditoría (que no reciben el ``request``)
puedan saber **quién** ejecutó una acción y **desde qué IP**.

Se usa ``threading.local`` porque el servidor WSGI/ASGI de Django atiende
cada petición en un hilo (WSGI) o en una tarea (ASGI). El valor se limpia
siempre en el bloque ``finally`` para no filtrar contexto entre
peticiones ni entre hilos reutilizados por el servidor.
"""

import threading

_local = threading.local()


def get_current_request():
    """
    Devuelve la petición HTTP en curso dentro del hilo actual.

    Returns
    -------
    django.http.HttpRequest | None
        La petición activa o ``None`` fuera de una petición (comandos,
        tareas de fondo, migraciones, tests sin cliente).
    """
    return getattr(_local, "request", None)


def get_current_user():
    """
    Devuelve el usuario autenticado de la petición en curso.

    Returns
    -------
    django.contrib.auth.models.User | None
        ``None`` si no hay petición, si el usuario es anónimo o si la
        autenticación aún no se ha resuelto.
    """
    request = get_current_request()
    usuario = getattr(request, "user", None)
    if usuario is not None and getattr(usuario, "is_authenticated", False):
        return usuario
    return None


def get_client_ip(request=None):
    """
    Obtiene la IP de origen de una petición.

    Considera ``X-Forwarded-For`` (útil detrás de un proxy) y cae a
    ``REMOTE_ADDR``. No valida la IP: eso lo hace el campo del modelo.

    Parameters
    ----------
    request : django.http.HttpRequest | None
        Petición de la que se quiere la IP. Si se omite, se usa la del
        hilo actual.
    """
    request = request or get_current_request()
    if request is None:
        return None

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        # El primer valor de la cadena es el cliente original.
        return forwarded.split(",")[0].strip() or None

    return request.META.get("REMOTE_ADDR") or None


class UsuarioActualMiddleware:
    """
    Publica la petición actual en un almacenamiento local del hilo.

    Debe declararse **después** de ``AuthenticationMiddleware`` en
    ``settings.MIDDLEWARE`` para que ``request.user`` ya esté resuelto
    cuando una vista o señal lo consulte.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None
