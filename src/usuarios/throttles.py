"""
Limitadores de tasa (throttling) de la aplicación 'usuarios'.

El objetivo es mitigar ataques de fuerza bruta contra el inicio de sesión
sin afectar al resto de la API, que ya tiene límites globales definidos en
``settings.REST_FRAMEWORK``.
"""

from rest_framework.throttling import SimpleRateThrottle


class LoginThrottle(SimpleRateThrottle):
    """
    Limita los intentos de inicio de sesión por dirección IP.

    La tasa se define en ``settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``
    bajo la clave ``login`` (por defecto ``10/min``).

    Notas
    -----
    Se limita por IP y no por usuario para que un atacante no pueda
    bloquear una cuenta ajena agotando sus intentos.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        """Construye una clave de caché estable por IP de origen."""
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
