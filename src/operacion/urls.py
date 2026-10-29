"""
Rutas de la aplicación 'operacion'.

Se registran bajo ``/api/`` desde ``poki_koa/urls.py``:

    /api/turnos/                  CRUD del catálogo de turnos
    /api/turnos/actual/           turno vigente
    /api/asignaciones/            CRUD de asignaciones
    /api/mis-cunas/               cunas del usuario autenticado
    /api/registros/               bitácora de auditoría (solo lectura)
    /api/registros/resumen/       conteo por acción
    /api/reportes/resumen/        métricas del dashboard
    /api/reportes/serie/          serie diaria
    /api/reportes/distribucion/   distribuciones agregadas
    /api/reportes/exportar/       exportación CSV
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AsignacionTurnoViewSet,
    DistribucionReporteView,
    ExportarReporteView,
    MisCunasView,
    RegistroActividadViewSet,
    ResumenReporteView,
    SerieReporteView,
    TurnoViewSet,
)

router = DefaultRouter()
router.register(r"turnos", TurnoViewSet)
router.register(r"asignaciones", AsignacionTurnoViewSet)
router.register(r"registros", RegistroActividadViewSet, basename="registro")

urlpatterns = [
    path("mis-cunas/", MisCunasView.as_view(), name="mis-cunas"),
    path("reportes/resumen/", ResumenReporteView.as_view(), name="reporte-resumen"),
    path("reportes/serie/", SerieReporteView.as_view(), name="reporte-serie"),
    path(
        "reportes/distribucion/",
        DistribucionReporteView.as_view(),
        name="reporte-distribucion",
    ),
    path("reportes/exportar/", ExportarReporteView.as_view(), name="reporte-exportar"),
    path("", include(router.urls)),
]
