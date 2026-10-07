"""
Motor de Detección y Evaluación de Alertas Clínicas Neonatales.

Este módulo centraliza la lógica de negocio para:
1. Evaluar signos vitales contra umbrales fisiológicos neonatales estándar.
2. Generar alertas clasificadas por severidad (Info, Advertencia, Crítica).
3. Gestionar el ciclo de vida de las alertas: deduplicación y autorresolución
   cuando los signos vitales regresan al rango seguro.
"""

from typing import Any

from django.utils import timezone

# Umbrales clínicos neonatales estándar (bpm, %, °C)
FC_BRADICARDIA_CRITICA = 80
FC_MIN_NORMAL = 100
FC_MAX_NORMAL = 160
FC_TAQUICARDIA_CRITICA = 180

SPO2_DESATURACION_CRITICA = 90
SPO2_MIN_NORMAL = 95
SPO2_MAX_VALIDO = 100

TEMP_HIPOTERMIA_CRITICA = 36.0
TEMP_MIN_NORMAL = 36.5
TEMP_MAX_NORMAL = 37.5
TEMP_FIEBRE_ALTA = 38.5

# Control de ejecución de señales para evitar bucles o facilitar tests
_PROCESAMIENTO_HABILITADO = True


def habilitar_procesamiento(habilitado: bool = True):
    """Permite pausar o reactivar temporalmente la evaluación automática."""
    global _PROCESAMIENTO_HABILITADO
    _PROCESAMIENTO_HABILITADO = habilitado


def esta_procesamiento_habilitado() -> bool:
    """Verifica si el procesamiento de alertas está activo."""
    return _PROCESAMIENTO_HABILITADO


def evaluar_signos_vitales(
    ritmo_cardiaco: int | None = None,
    spo2: int | None = None,
    temperatura: float | None = None,
    canula_ok: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Función pura para evaluar un conjunto de lecturas clínicas contra los
    umbrales fisiológicos neonatales.

    Retorna una lista de diccionarios con las anomalías detectadas:
    [
        {
            "tipo": "ritmo_cardiaco" | "spo2" | "temperatura" | "canula",
            "nivel": "Advertencia" | "Critica",
            "mensaje": str,
            "valor_leido": float | None
        },
        ...
    ]
    """
    anomalias: list[dict[str, Any]] = []

    # 1. Evaluación de Frecuencia Cardíaca (ritmo_cardiaco)
    if ritmo_cardiaco is not None:
        fc = ritmo_cardiaco
        if fc < FC_BRADICARDIA_CRITICA:
            anomalias.append(
                {
                    "tipo": "ritmo_cardiaco",
                    "nivel": "Critica",
                    "mensaje": (
                        f"Bradicardia severa: {fc} bpm (umbral crítico < {FC_BRADICARDIA_CRITICA} bpm)"
                    ),
                    "valor_leido": float(fc),
                }
            )
        elif fc < FC_MIN_NORMAL:
            anomalias.append(
                {
                    "tipo": "ritmo_cardiaco",
                    "nivel": "Advertencia",
                    "mensaje": (
                        f"Bradicardia moderada: {fc} bpm (rango normal {FC_MIN_NORMAL}-{FC_MAX_NORMAL} bpm)"
                    ),
                    "valor_leido": float(fc),
                }
            )
        elif fc > FC_TAQUICARDIA_CRITICA:
            anomalias.append(
                {
                    "tipo": "ritmo_cardiaco",
                    "nivel": "Critica",
                    "mensaje": (
                        f"Taquicardia severa: {fc} bpm (umbral crítico > {FC_TAQUICARDIA_CRITICA} bpm)"
                    ),
                    "valor_leido": float(fc),
                }
            )
        elif fc > FC_MAX_NORMAL:
            anomalias.append(
                {
                    "tipo": "ritmo_cardiaco",
                    "nivel": "Advertencia",
                    "mensaje": (
                        f"Taquicardia moderada: {fc} bpm (rango normal {FC_MIN_NORMAL}-{FC_MAX_NORMAL} bpm)"
                    ),
                    "valor_leido": float(fc),
                }
            )

    # 2. Evaluación de Saturación de Oxígeno (spo2)
    if spo2 is not None:
        sat = spo2
        if sat < 0 or sat > SPO2_MAX_VALIDO:
            anomalias.append(
                {
                    "tipo": "spo2",
                    "nivel": "Advertencia",
                    "mensaje": f"Lectura anómala de sensor SpO2: {sat}% (rango físico 0-100%)",
                    "valor_leido": float(sat),
                }
            )
        elif sat < SPO2_DESATURACION_CRITICA:
            anomalias.append(
                {
                    "tipo": "spo2",
                    "nivel": "Critica",
                    "mensaje": (
                        f"Desaturación de oxígeno crítica: {sat}% (umbral crítico < {SPO2_DESATURACION_CRITICA}%)"
                    ),
                    "valor_leido": float(sat),
                }
            )
        elif sat < SPO2_MIN_NORMAL:
            anomalias.append(
                {
                    "tipo": "spo2",
                    "nivel": "Advertencia",
                    "mensaje": (
                        f"Saturación de oxígeno baja: {sat}% (rango normal >= {SPO2_MIN_NORMAL}%)"
                    ),
                    "valor_leido": float(sat),
                }
            )

    # 3. Evaluación de Temperatura corporal
    if temperatura is not None:
        temp = float(temperatura)
        if temp < TEMP_HIPOTERMIA_CRITICA:
            anomalias.append(
                {
                    "tipo": "temperatura",
                    "nivel": "Critica",
                    "mensaje": (
                        f"Hipotermia severa detectada: {temp:.1f} °C (umbral crítico < {TEMP_HIPOTERMIA_CRITICA} °C)"
                    ),
                    "valor_leido": temp,
                }
            )
        elif temp < TEMP_MIN_NORMAL:
            anomalias.append(
                {
                    "tipo": "temperatura",
                    "nivel": "Advertencia",
                    "mensaje": (
                        f"Hipotermia leve detectada: {temp:.1f} °C (rango normal {TEMP_MIN_NORMAL}-{TEMP_MAX_NORMAL} °C)"
                    ),
                    "valor_leido": temp,
                }
            )
        elif temp > TEMP_FIEBRE_ALTA:
            anomalias.append(
                {
                    "tipo": "temperatura",
                    "nivel": "Critica",
                    "mensaje": (
                        f"Hipertermia crítica detectada: {temp:.1f} °C (umbral crítico > {TEMP_FIEBRE_ALTA} °C)"
                    ),
                    "valor_leido": temp,
                }
            )
        elif temp > TEMP_MAX_NORMAL:
            anomalias.append(
                {
                    "tipo": "temperatura",
                    "nivel": "Advertencia",
                    "mensaje": f"Fiebre detectada ({temp:.1f} °C)",
                    "valor_leido": temp,
                }
            )

    # 4. Evaluación de Dispositivos / Sensores (cánula de oxígeno)
    if canula_ok is False:
        anomalias.append(
            {
                "tipo": "canula",
                "nivel": "Critica",
                "mensaje": "Desconexión de cánula de oxígeno o falla de flujo detectada",
                "valor_leido": 0.0,
            }
        )

    return anomalias


def procesar_alertas_cuna(cuna) -> list[Any]:
    """
    Evalúa los signos vitales actuales de una Cuna, gestiona el ciclo de vida
    de las alertas en la base de datos (creación, deduplicación y autorresolución)
    y retorna la lista de instancias de Alerta activas/nuevas generadas.
    """
    if not esta_procesamiento_habilitado():
        return []

    # Import diferido para evitar ciclos de importación con models
    from cunas.models import Alerta

    anomalias = evaluar_signos_vitales(
        ritmo_cardiaco=cuna.ritmo_cardiaco,
        spo2=cuna.spo2,
        temperatura=cuna.temperatura,
        canula_ok=cuna.canula_ok,
    )

    alertas_procesadas: list[Alerta] = []
    tipos_con_anomalia = {a["tipo"] for a in anomalias}

    # 1. Registrar o actualizar anomalías detectadas
    for anomalia in anomalias:
        tipo = anomalia["tipo"]
        nivel = anomalia["nivel"]
        mensaje = anomalia["mensaje"]
        valor_leido = anomalia.get("valor_leido")

        # Buscar si ya existe una alerta activa del mismo tipo en esta cuna
        alerta_activa = (
            Alerta.objects.filter(cuna=cuna, tipo=tipo, activa=True)
            .order_by("-fecha_hora")
            .first()
        )

        if alerta_activa:
            if alerta_activa.nivel == nivel:
                # Mismo nivel de severidad: actualizar mensaje, valor y hora para evitar spam
                alerta_activa.mensaje = mensaje
                alerta_activa.valor_leido = valor_leido
                alerta_activa.fecha_hora = timezone.now()
                # Asegurar asociación con el paciente actual si cambió
                if cuna.paciente and alerta_activa.paciente != cuna.paciente:
                    alerta_activa.paciente = cuna.paciente
                alerta_activa.save(
                    update_fields=["mensaje", "valor_leido", "fecha_hora", "paciente"]
                )
                alertas_procesadas.append(alerta_activa)
                continue
            else:
                # El nivel de severidad cambió (ej: de Advertencia a Crítica o viceversa)
                # Resolvemos la anterior y creamos la nueva con el nuevo nivel
                alerta_activa.activa = False
                alerta_activa.save(update_fields=["activa"])

        # Crear nueva alerta activa
        nueva_alerta = Alerta.objects.create(
            cuna=cuna,
            paciente=cuna.paciente,
            tipo=tipo,
            nivel=nivel,
            mensaje=mensaje,
            valor_leido=valor_leido,
            activa=True,
            fecha_hora=timezone.now(),
        )
        alertas_procesadas.append(nueva_alerta)

    # 2. Autorresolución: Si un signo vital volvió a la normalidad, desactivar alertas previas
    tipos_evaluados = []
    if cuna.ritmo_cardiaco is not None:
        tipos_evaluados.append("ritmo_cardiaco")
    if cuna.spo2 is not None:
        tipos_evaluados.append("spo2")
    if cuna.temperatura is not None:
        tipos_evaluados.append("temperatura")
    if cuna.canula_ok is not None:
        tipos_evaluados.append("canula")

    for tipo in tipos_evaluados:
        if tipo not in tipos_con_anomalia:
            # Los signos para este tipo están normales: desactivar alertas activas
            Alerta.objects.filter(cuna=cuna, tipo=tipo, activa=True).update(activa=False)

    return alertas_procesadas

