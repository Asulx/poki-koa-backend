"""Generador automatizado de casos, colecciones y matrices de prueba para QA.

Este script procesa las definiciones de prueba de la Entrega 2, generando
los artefactos necesarios (casos JSON, colecciones de Thunder Client,
archivos de peticiones HTTP, fixtures de base de datos y la matriz de pruebas)
sin depender directamente de la infraestructura de Django.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from generar_bruno_entrega2 import main as generar_bruno

# Directorios y configuración temporal base
DIRECTORIO_RAIZ = Path(__file__).resolve().parents[1]
DIRECTORIO_SALIDA_QA = DIRECTORIO_RAIZ / "qa" / "entrega2"
DIRECTORIO_DOCUMENTACION = DIRECTORIO_RAIZ / "docs" / "entrega2"

TIEMPO_ACTUAL_UTC = datetime.now(timezone.utc)
FECHA_MARCA_TIEMPO = TIEMPO_ACTUAL_UTC.isoformat()
FECHA_ACTUAL = TIEMPO_ACTUAL_UTC.date()

VARIABLES_ENTORNO = {
    "base_url": "http://127.0.0.1:8000",
    "ayer": str(FECHA_ACTUAL - timedelta(days=1)),
    "hoy": str(FECHA_ACTUAL),
    "manana": str(FECHA_ACTUAL + timedelta(days=1)),
}

LISTA_CASOS_PRUEBA = []


"""
Guarda un objeto estructurado en formato JSON con indentación estándar.

@param ruta_destino - Ruta del archivo donde se almacenará el contenido.
@param objeto_datos - Datos en formato diccionario o lista a serializar.
@returns None - No retorna valores, escribe directamente en disco.
"""


def guardar_archivo_json(ruta_destino: Path, objeto_datos: dict | list) -> None:
    ruta_destino.write_text(
        json.dumps(objeto_datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


"""
Construye un paso individual de petición HTTP estructurada.

@param metodo_http - Verbo HTTP a utilizar (ej. 'GET', 'POST', 'PATCH').
@param ruta_endpoint - Ruta relativa del endpoint de la API.
@param codigo_estado - Código de estado HTTP esperado en la respuesta.
@param cuerpo_datos - Cuerpo opcional en formato JSON para la petición.
@param igualdades - Diccionario de campos y valores esperados en la respuesta.
@param llaves_requeridas - Lista de claves obligatorias que deben estar presentes.
@param longitud_esperada - Tamaño esperado de la lista o respuesta devuelta.
@returns dict - Diccionario con la estructura completa del paso de prueba.
"""


def generar_paso_peticion(
    metodo_http: str,
    ruta_endpoint: str,
    codigo_estado: int,
    cuerpo_datos: dict | None = None,
    igualdades: dict | None = None,
    llaves_requeridas: list | None = None,
    longitud_esperada: int | None = None,
) -> dict:
    resultado = {"method": metodo_http, "path": ruta_endpoint, "status": codigo_estado}
    if cuerpo_datos is not None:
        resultado["body"] = cuerpo_datos
    if igualdades:
        resultado["equals"] = igualdades
    if llaves_requeridas:
        resultado["keys"] = llaves_requeridas
    if longitud_esperada is not None:
        resultado["length"] = longitud_esperada
    return resultado


"""
Registra y añade un caso de prueba a la lista global de ejecución.

@param identificador_caso - Código único del caso (ej. 'B01', 'M01').
@param titulo_descripcion - Descripción breve del objetivo del caso.
@param criterio_aceptacion - Criterio de aceptación asociado (ej. 'B-CA1').
@param tecnica_prueba - Técnica de diseño de pruebas aplicada.
@param peticion_principal - Diccionario con la solicitud HTTP principal.
@param pasos_verificacion - Lista opcional de pasos de seguimiento (ej. aserciones GET).
@returns None - Almacena el caso en la estructura global LISTA_CASOS_PRUEBA.
"""


def registrar_caso_prueba(
    identificador_caso: str,
    titulo_descripcion: str,
    criterio_aceptacion: str,
    tecnica_prueba: str,
    peticion_principal: dict,
    pasos_verificacion: list | None = None,
) -> None:
    LISTA_CASOS_PRUEBA.append(
        {
            "id": identificador_caso,
            "title": titulo_descripcion,
            "hu": "US-01" if identificador_caso[0] == "B" else "US-02",
            "ca": criterio_aceptacion,
            "technique": tecnica_prueba,
            "steps": [peticion_principal] + (pasos_verificacion or []),
        }
    )


"""
Configura y añade un caso de prueba parametrizado para el dominio de bebés.

@param numero_secuencia - Número entero identificador del caso de bebé.
@param titulo_caso - Título descriptivo del escenario de prueba.
@param criterio_aceptacion - Criterio de aceptación evaluado.
@param tecnica_prueba - Nombre de la técnica de prueba aplicada.
@param cambios_cuerpo - Diccionario con modificaciones sobre el cuerpo base.
@param campos_omitidos - Tupla de campos a eliminar del cuerpo de la petición.
@param error_esperado - Nombre del campo que arrojará error de validación, si aplica.
@returns None - Registra el caso mediante la función de adición.
"""


def construir_caso_bebe(
    numero_secuencia: int,
    titulo_caso: str,
    criterio_aceptacion: str,
    tecnica_prueba: str,
    cambios_cuerpo: dict | None = None,
    campos_omitidos: tuple = (),
    error_esperado: str | None = None,
) -> None:
    id_caso = f"B{numero_secuencia:02}"
    cuerpo_base = {
        "identificador": f"QA-{id_caso}",
        "nombre_completo": "Paciente ficticio QA",
        "edad_meses": 0,
        "sexo": "F",
        "peso": 3.2,
        "fecha_nacimiento": "{{ayer}}",
        "medico_a_cargo": 910001,
    }

    if cambios_cuerpo:
        cuerpo_base.update(cambios_cuerpo)

    for campo in campos_omitidos:
        cuerpo_base.pop(campo, None)

    igualdades_esperadas = (
        None if error_esperado else {k: v for k, v in cuerpo_base.items()}
    )
    pasos_verificacion = []

    if error_esperado and cuerpo_base.get("identificador") == f"QA-{id_caso}":
        pasos_verificacion.append(
            generar_paso_peticion(
                "GET",
                f"/api/bebes/?identificador=QA-{id_caso}",
                200,
                longitud_esperada=0,
            )
        )

    peticion_http = generar_paso_peticion(
        "POST",
        "/api/bebes/",
        400 if error_esperado else 201,
        cuerpo_base,
        igualdades_esperadas,
        [error_esperado] if error_esperado else None,
    )

    registrar_caso_prueba(
        id_caso,
        titulo_caso,
        criterio_aceptacion,
        tecnica_prueba,
        peticion_http,
        pasos_verificacion,
    )


# Generación de casos para Bebés
construir_caso_bebe(
    1,
    "Registro válido con médico existente",
    "B-CA1,B-CA4",
    "Equivalencia válida / negocio",
)
construir_caso_bebe(
    2,
    "Identificador obligatorio ausente",
    "B-CA2",
    "Equivalencia inválida",
    campos_omitidos=("identificador",),
    error_esperado="identificador",
)
construir_caso_bebe(
    3,
    "Identificador ya registrado",
    "B-CA2",
    "Negocio: unicidad",
    {"identificador": "QA-BASE-1"},
    error_esperado="identificador",
)
construir_caso_bebe(
    4,
    "Nombre vacío",
    "B-CA2",
    "Equivalencia inválida",
    {"nombre_completo": ""},
    error_esperado="nombre_completo",
)

for num, tamano in [(5, 199), (6, 200), (7, 201)]:
    construir_caso_bebe(
        num,
        f"Nombre de {tamano} caracteres",
        "B-CA2",
        "Límite superior de longitud",
        {"nombre_completo": "N" * tamano},
        error_esperado="nombre_completo" if tamano > 200 else None,
    )

construir_caso_bebe(
    8,
    "Peso no numérico",
    "B-CA3",
    "Equivalencia inválida: tipo",
    {"peso": "abc"},
    error_esperado="peso",
)

for num, peso_val in [(9, -0.01), (10, 0), (11, 0.01)]:
    construir_caso_bebe(
        num,
        f"Peso {peso_val}",
        "B-CA3",
        "Límite inferior: peso > 0",
        {"peso": peso_val},
        error_esperado="peso" if peso_val <= 0 else None,
    )

construir_caso_bebe(
    12,
    "Peso y fecha opcionales nulos",
    "B-CA3",
    "Equivalencia válida: ausencia opcional",
    {"peso": None, "fecha_nacimiento": None},
)

for num, etiqueta_fecha in [(13, "ayer"), (14, "hoy"), (15, "manana")]:
    construir_caso_bebe(
        num,
        f"Fecha de nacimiento: {etiqueta_fecha}",
        "B-CA3",
        "Límite temporal",
        {"fecha_nacimiento": "{{" + etiqueta_fecha + "}}"},
        error_esperado="fecha_nacimiento" if etiqueta_fecha == "manana" else None,
    )

construir_caso_bebe(
    16,
    "Sexo fuera del catálogo",
    "B-CA2",
    "Equivalencia inválida: elección",
    {"sexo": "X"},
    error_esperado="sexo",
)
construir_caso_bebe(
    17,
    "Médico inexistente",
    "B-CA4",
    "Negocio: integridad referencial",
    {"medico_a_cargo": 999999},
    error_esperado="medico_a_cargo",
)

registrar_caso_prueba(
    "B18",
    "Modificar diagnóstico sin perder otros datos",
    "B-CA5",
    "Negocio: actualización parcial",
    generar_paso_peticion(
        "PATCH",
        "/api/bebes/910001/",
        200,
        {"diagnostico": "Observación QA actualizada"},
        {
            "diagnostico": "Observación QA actualizada",
            "identificador": "QA-BASE-1",
            "peso": 3.2,
            "medico_a_cargo": 910001,
        },
    ),
    [
        generar_paso_peticion(
            "GET",
            "/api/bebes/910001/",
            200,
            igualdades={
                "diagnostico": "Observación QA actualizada",
                "peso": 3.2,
                "medico_a_cargo": 910001,
            },
        )
    ],
)

registrar_caso_prueba(
    "B19",
    "Edición inválida no guarda ni siquiera los campos válidos",
    "B-CA3,B-CA5",
    "Negocio: rechazo atómico",
    generar_paso_peticion(
        "PATCH",
        "/api/bebes/910001/",
        400,
        {"peso": 0, "diagnostico": "NO DEBE GUARDARSE"},
        llaves_requeridas=["peso"],
    ),
    [
        generar_paso_peticion(
            "GET",
            "/api/bebes/910001/",
            200,
            igualdades={"peso": 3.2, "diagnostico": "Observación QA actualizada"},
        )
    ],
)

registrar_caso_prueba(
    "B20",
    "Consultar paciente inexistente",
    "B-CA5",
    "Equivalencia inválida: recurso",
    generar_paso_peticion(
        "GET", "/api/bebes/999999/", 404, llaves_requeridas=["detail"]
    ),
)

registrar_caso_prueba(
    "B21",
    "Recuperar datos para edición y relaciones",
    "B-CA5",
    "Negocio: precarga de edición",
    generar_paso_peticion(
        "GET",
        "/api/bebes/910001/",
        200,
        igualdades={
            "identificador": "QA-BASE-1",
            "medico_nombre": "Profesional ficticio QA",
            "cuna": "QA-CUNA-1",
            "medicamentos.0.id": 910001,
        },
    ),
)

registrar_caso_prueba(
    "B22",
    "Eliminar paciente libera cuna y elimina medicación asociada",
    "B-CA6",
    "Negocio: cascada y SET_NULL (alcance adicional)",
    generar_paso_peticion("DELETE", "/api/bebes/910003/", 204),
    [
        generar_paso_peticion(
            "GET", "/api/bebes/910003/", 404, llaves_requeridas=["detail"]
        ),
        generar_paso_peticion(
            "GET", "/api/medicamentos/910003/", 404, llaves_requeridas=["detail"]
        ),
        generar_paso_peticion(
            "GET", "/api/cunas/910002/", 200, igualdades={"paciente": None}
        ),
    ],
)


# ============================================================================
# Definición de Casos de Catálogo de Medicamentos (Módulo M)
# ============================================================================

RUTA_ENDPOINT_CATALOGO = "/api/catalogo-medicamentos/"


"""
Configura y añade un caso de prueba para el catálogo de medicamentos.

@param numero_secuencia - Número entero identificador del medicamento en QA.
@param titulo_caso - Título descriptivo del escenario de prueba.
@param tecnica_prueba - Nombre de la técnica de prueba aplicada.
@param cambios_cuerpo - Diccionario con valores personalizados para el cuerpo.
@param campos_omitidos - Tupla de campos a excluir de la solicitud.
@param error_esperado - Nombre del campo que arrojará error de validación, si aplica.
@returns None - Registra el caso mediante la función de adición.
"""


def construir_caso_catalogo(
    numero_secuencia: int,
    titulo_caso: str,
    tecnica_prueba: str,
    cambios_cuerpo: dict | None = None,
    campos_omitidos: tuple = (),
    error_esperado: str | None = None,
) -> None:
    id_caso = f"M{numero_secuencia:02}"
    cuerpo_base = {
        "nombre": f"Producto ficticio M{numero_secuencia:02}",
        "principio_activo": "Sustancia QA",
        "dosis_mg": "1.00",
        "stock": 10,
    }

    if cambios_cuerpo:
        cuerpo_base.update(cambios_cuerpo)

    for campo in campos_omitidos:
        cuerpo_base.pop(campo, None)

    peticion_http = generar_paso_peticion(
        "POST",
        RUTA_ENDPOINT_CATALOGO,
        400 if error_esperado else 201,
        cuerpo_base,
        igualdades=None if error_esperado else cuerpo_base,
        llaves_requeridas=[error_esperado] if error_esperado else None,
    )

    registrar_caso_prueba(
        id_caso,
        titulo_caso,
        "M-CA1,M-CA3",
        tecnica_prueba,
        peticion_http,
    )


# Generación de casos para el Catálogo
construir_caso_catalogo(1, "Registro válido en catálogo", "Equivalencia válida")
construir_caso_catalogo(
    2,
    "Nombre obligatorio",
    "Equivalencia inválida",
    campos_omitidos=("nombre",),
    error_esperado="nombre",
)
construir_caso_catalogo(
    3,
    "Principio activo vacío",
    "Equivalencia inválida",
    {"principio_activo": " "},
    error_esperado="principio_activo",
)
construir_caso_catalogo(
    4, "Nombre de 150 caracteres", "Límite superior", {"nombre": "N" * 150}
)
construir_caso_catalogo(
    5,
    "Nombre de 151 caracteres",
    "Límite excedido",
    {"nombre": "N" * 151},
    error_esperado="nombre",
)
construir_caso_catalogo(
    6,
    "Principio activo de 150 caracteres",
    "Límite superior",
    {"principio_activo": "P" * 150},
)
construir_caso_catalogo(
    7,
    "Principio activo de 151 caracteres",
    "Límite excedido",
    {"principio_activo": "P" * 151},
    error_esperado="principio_activo",
)
construir_caso_catalogo(
    8,
    "Dosis no numérica",
    "Equivalencia inválida",
    {"dosis_mg": "abc"},
    error_esperado="dosis_mg",
)
construir_caso_catalogo(
    9,
    "Dosis cero",
    "Límite inferior excluido",
    {"dosis_mg": "0.00"},
    error_esperado="dosis_mg",
)
construir_caso_catalogo(
    10, "Dosis mínima 0.01 mg", "Límite inferior incluido", {"dosis_mg": "0.01"}
)
construir_caso_catalogo(
    11,
    "Dosis con exceso de decimales",
    "Precisión decimal",
    {"dosis_mg": "0.001"},
    error_esperado="dosis_mg",
)
construir_caso_catalogo(
    12, "Stock cero", "Límite inferior excluido", {"stock": 0}, error_esperado="stock"
)
construir_caso_catalogo(
    13, "Stock mínimo una unidad", "Límite inferior incluido", {"stock": 1}
)
construir_caso_catalogo(
    14,
    "Stock fraccionario",
    "Equivalencia inválida",
    {"stock": 1.5},
    error_esperado="stock",
)
construir_caso_catalogo(
    15,
    "Stock obligatorio",
    "Equivalencia inválida",
    campos_omitidos=("stock",),
    error_esperado="stock",
)
construir_caso_catalogo(
    16,
    "Dosis obligatoria",
    "Equivalencia inválida",
    campos_omitidos=("dosis_mg",),
    error_esperado="dosis_mg",
)

registrar_caso_prueba(
    "M17",
    "Consulta para precarga",
    "M-CA2",
    "Negocio: recuperar producto",
    generar_paso_peticion(
        "GET",
        RUTA_ENDPOINT_CATALOGO + "910001/",
        200,
        igualdades={
            "nombre": "Producto base QA",
            "principio_activo": "Sustancia QA",
            "dosis_mg": "1.00",
            "stock": 10,
        },
    ),
)

registrar_caso_prueba(
    "M18",
    "Modificar stock y conservar otros campos",
    "M-CA2",
    "Negocio: persistencia",
    generar_paso_peticion(
        "PATCH",
        RUTA_ENDPOINT_CATALOGO + "910001/",
        200,
        {"stock": 5},
        {"stock": 5, "dosis_mg": "1.00"},
    ),
    [
        generar_paso_peticion(
            "GET",
            RUTA_ENDPOINT_CATALOGO + "910001/",
            200,
            igualdades={"stock": 5, "nombre": "Producto base QA"},
        )
    ],
)

registrar_caso_prueba(
    "M19",
    "Edición inválida no guarda cambios parciales",
    "M-CA2,M-CA3",
    "Negocio: rechazo atómico",
    generar_paso_peticion(
        "PATCH",
        RUTA_ENDPOINT_CATALOGO + "910001/",
        400,
        {"stock": -1, "nombre": "NO GUARDAR"},
        llaves_requeridas=["stock"],
    ),
    [
        generar_paso_peticion(
            "GET",
            RUTA_ENDPOINT_CATALOGO + "910001/",
            200,
            igualdades={"stock": 5, "nombre": "Producto base QA"},
        )
    ],
)

registrar_caso_prueba(
    "M20",
    "Producto inexistente",
    "M-CA2",
    "Equivalencia inválida",
    generar_paso_peticion(
        "GET", RUTA_ENDPOINT_CATALOGO + "999999/", 404, llaves_requeridas=["detail"]
    ),
)

registrar_caso_prueba(
    "M21",
    "Modificar todos los campos",
    "M-CA2",
    "Negocio: actualización completa",
    generar_paso_peticion(
        "PUT",
        RUTA_ENDPOINT_CATALOGO + "910001/",
        200,
        {
            "nombre": "Producto actualizado QA",
            "principio_activo": "Sustancia nueva QA",
            "dosis_mg": "2.50",
            "stock": 20,
        },
    ),
    [
        generar_paso_peticion(
            "GET",
            RUTA_ENDPOINT_CATALOGO + "910001/",
            200,
            igualdades={
                "nombre": "Producto actualizado QA",
                "principio_activo": "Sustancia nueva QA",
                "dosis_mg": "2.50",
                "stock": 20,
            },
        )
    ],
)

registrar_caso_prueba(
    "M22",
    "PUT incompleto conserva el producto",
    "M-CA2,M-CA3",
    "Negocio: campos requeridos",
    generar_paso_peticion(
        "PUT",
        RUTA_ENDPOINT_CATALOGO + "910001/",
        400,
        {"nombre": "NO GUARDAR"},
        llaves_requeridas=["principio_activo", "dosis_mg", "stock"],
    ),
    [
        generar_paso_peticion(
            "GET",
            RUTA_ENDPOINT_CATALOGO + "910001/",
            200,
            igualdades={"nombre": "Producto actualizado QA", "stock": 20},
        )
    ],
)

# Actualización dinámica de contadores para validación de longitud en colecciones
conteo_entidades = {"B": 3, "M": 1}
for caso in LISTA_CASOS_PRUEBA:
    primer_paso = caso["steps"][0]
    if primer_paso["method"] == "POST":
        grupo_id = caso["id"][0]
        conteo_entidades[grupo_id] += int(primer_paso["status"] == 201)
        caso["steps"].append(
            generar_paso_peticion(
                "GET",
                primer_paso["path"],
                200,
                longitud_esperada=conteo_entidades[grupo_id],
            )
        )


# ============================================================================
# Construcción de Solicitudes y Exportación de Artefactos
# ============================================================================

"""
Genera un UUID determinista v5 basado en URL para los elementos de exportación.

@param valor_semilla - Cadena de texto base para generar el hash identificador.
@returns str - Representación en cadena del UUID generado.
"""


def generar_uuid_objeto(valor_semilla: str) -> str:
    return str(uuid5(NAMESPACE_URL, "poki-koa/entrega2/" + valor_semilla))


"""
Formatea un valor de prueba para su uso en consultas de aserción.

@param valor - Valor primitivo o complejo a formatear.
@returns str - El valor convertido en cadena o serializado en JSON.
"""


def formatear_valor_texto(valor: any) -> str:
    return valor if isinstance(valor, str) else json.dumps(valor)


"""
Construye la estructura de una solicitud compatible con Thunder Client.

@param caso - Diccionario que describe el caso de prueba completo.
@param item - Diccionario del paso HTTP específico a procesar.
@param indice_paso - Índice numérico del paso dentro del caso.
@param orden_secuencia - Número de orden global de la solicitud.
@returns dict - Diccionario con la configuración completa de la petición.
"""


def construir_solicitud_thunder_client(
    caso: dict, item: dict, indice_paso: int, orden_secuencia: int
) -> dict:
    nombre_solicitud = (
        caso["id"] + (f".v{indice_paso}" if indice_paso else "") + " — " + caso["title"]
    )
    lista_tests = [
        {
            "type": "res-code",
            "custom": "",
            "action": "equal",
            "value": str(item["status"]),
        }
    ]

    for clave, valor in item.get("equals", {}).items():
        consulta_json = re.sub(r"\.(\d+)(?=\.|$)", r"[\1]", "json." + clave)
        lista_tests.append(
            {
                "type": "json",
                "custom": consulta_json,
                "action": "equal",
                "value": formatear_valor_texto(valor),
            }
        )

    for clave in item.get("keys", []):
        lista_tests.append(
            {"type": "json", "custom": "json." + clave, "action": "exists", "value": ""}
        )

    if "length" in item:
        lista_tests.append(
            {
                "type": "json",
                "custom": "json",
                "action": "count",
                "value": str(item["length"]),
            }
        )

    solicitud = {
        "_id": generar_uuid_objeto(nombre_solicitud),
        "colId": generar_uuid_objeto("collection"),
        "containerId": generar_uuid_objeto(caso["hu"]),
        "name": nombre_solicitud,
        "url": "{{base_url}}" + item["path"],
        "method": item["method"],
        "sortNum": orden_secuencia * 10000,
        "created": FECHA_MARCA_TIEMPO,
        "modified": FECHA_MARCA_TIEMPO,
        "headers": [{"name": "Content-Type", "value": "application/json"}],
        "params": [],
        "tests": lista_tests,
        "description": f"{caso['ca']} | {caso['technique']}. Ejecutar en orden; ver docs/entrega2.",
    }

    if "body" in item:
        solicitud["body"] = {
            "type": "json",
            "raw": json.dumps(item["body"], ensure_ascii=False, indent=2),
            "form": [],
        }

    return solicitud


# ============================================================================
# Función Principal de Ejecución y Orquestación
# ============================================================================

"""
Función principal de orquestación para generar todos los artefactos de QA.

@param - No recibe parámetros directos.
@returns None - Crea directorios, archivos JSON, peticiones HTTP y documentación Markdown.
"""


def main() -> None:
    DIRECTORIO_SALIDA_QA.mkdir(parents=True, exist_ok=True)
    DIRECTORIO_DOCUMENTACION.mkdir(parents=True, exist_ok=True)

    # 1. Guardar manifiesto JSON de casos
    guardar_archivo_json(
        DIRECTORIO_SALIDA_QA / "casos.json", {"schema": 1, "cases": LISTA_CASOS_PRUEBA}
    )

    solicitudes_thunder = []
    lineas_http = [f"@{key} = {value}" for key, value in VARIABLES_ENTORNO.items()]

    for caso in LISTA_CASOS_PRUEBA:
        for indice, item in enumerate(caso["steps"]):
            solicitudes_thunder.append(
                construir_solicitud_thunder_client(
                    caso, item, indice, len(solicitudes_thunder) + 1
                )
            )
            lineas_http.extend(
                [
                    "",
                    f"### {caso['id']} paso {indice + 1}: {caso['title']}",
                    f"# Esperado: HTTP {item['status']}; {json.dumps({k: v for k, v in item.items() if k in ('equals', 'keys', 'length')}, ensure_ascii=False)}",
                    f"{item['method']} {{{{base_url}}}}{item['path']}",
                    "Content-Type: application/json",
                    "",
                ]
            )
            if "body" in item:
                lineas_http.append(
                    json.dumps(item["body"], ensure_ascii=False, indent=2)
                )

    # 2. Guardar colección de Thunder Client
    guardar_archivo_json(
        DIRECTORIO_SALIDA_QA / "thunder-collection_entrega2.json",
        {
            "client": "Thunder Client",
            "collectionName": "Poki Koa — Entrega 2 — 44 casos",
            "dateExported": FECHA_MARCA_TIEMPO,
            "version": "1.1",
            "folders": [
                {
                    "_id": generar_uuid_objeto(hu),
                    "name": hu,
                    "containerId": "",
                    "created": FECHA_MARCA_TIEMPO,
                    "sortNum": numero * 10000,
                }
                for numero, hu in enumerate(["US-01", "US-02"], 1)
            ],
            "requests": solicitudes_thunder,
        },
    )

    # 3. Guardar archivo de entorno local
    guardar_archivo_json(
        DIRECTORIO_SALIDA_QA / "thunder-environment_local.json",
        {
            "client": "Thunder Client",
            "environmentName": "Poki Koa — Demo local",
            "dateExported": FECHA_MARCA_TIEMPO,
            "version": "1.0",
            "variables": [
                {"name": k, "value": v} for k, v in VARIABLES_ENTORNO.items()
            ],
        },
    )

    # 4. Guardar archivo de peticiones HTTP
    (DIRECTORIO_SALIDA_QA / "peticiones.http").write_text(
        "\n".join(lineas_http) + "\n", encoding="utf-8"
    )

    # 5. Generación de Fixtures para la Base de Datos
    fixtures = [
        {
            "model": "cunas.medico",
            "pk": 910001,
            "fields": {"nombre_completo": "Profesional ficticio QA", "turno": "Prueba"},
        }
    ]

    for pk, etiqueta in [(910001, "uno"), (910002, "dos"), (910003, "tres")]:
        fixtures.append(
            {
                "model": "cunas.bebe",
                "pk": pk,
                "fields": {
                    "identificador": f"QA-BASE-{pk - 910000}",
                    "nombre_completo": f"Paciente base {etiqueta} QA",
                    "edad_meses": 0,
                    "sexo": "F",
                    "peso": 3.2,
                    "medico_a_cargo": 910001,
                    "fecha_nacimiento": str(FECHA_ACTUAL - timedelta(days=1)),
                    "fecha_ingreso": FECHA_MARCA_TIEMPO,
                },
            }
        )
        fixtures.append(
            {
                "model": "cunas.medicamento",
                "pk": pk,
                "fields": {
                    "paciente": pk,
                    "nombre": "Insumo ficticio base QA",
                    "dosis": "1 unidad de prueba",
                    "via": "IV",
                    "hora": "08:00:00",
                    "estado": "Pendiente",
                },
            }
        )

    for pk, paciente_id in [(910001, 910001), (910002, 910003)]:
        fixtures.append(
            {
                "model": "cunas.cuna",
                "pk": pk,
                "fields": {
                    "identificador": f"QA-CUNA-{pk - 910000}",
                    "paciente": paciente_id,
                    "ritmo_cardiaco": 130,
                    "spo2": 98,
                    "temperatura": 36.8,
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": False,
                    "ultima_actualizacion": FECHA_MARCA_TIEMPO,
                },
            }
        )

    fixtures.append(
        {
            "model": "cunas.medicamentocatalogo",
            "pk": 910001,
            "fields": {
                "nombre": "Producto base QA",
                "principio_activo": "Sustancia QA",
                "dosis_mg": "1.00",
                "stock": 10,
            },
        }
    )
    guardar_archivo_json(DIRECTORIO_SALIDA_QA / "datos_demo.json", fixtures)

    # 6. Generación de la Matriz de Casos en Markdown
    lineas_matriz = [
        "# Matriz de casos del Entregable 2",
        "",
        "22 casos por API, 44 en total.",
        "Los pasos `.vN` verifican persistencia y efectos; no se cuentan como casos adicionales.",
        "Precondición común: cargar datos_demo.json en la base aislada y ejecutar B01…B22, luego M01…M22.",
        "Todos los resultados de esta matriz son **esperados**, no ejecuciones acreditadas.",
        "",
        "| Caso | HU / CA propuesto | Objetivo | Técnica | Petición | Esperado |",
        "|---|---|---|---|---|---|",
    ]

    for caso in LISTA_CASOS_PRUEBA:
        paso_principal = caso["steps"][0]
        lineas_matriz.append(
            f"| {caso['id']} | {caso['hu']} / {caso['ca']} | {caso['title']} | {caso['technique']} | `{paso_principal['method']} {paso_principal['path']}` | {paso_principal['status']}; comprobar cuerpo y pasos posteriores |"
        )

    lineas_matriz.extend(
        [
            "",
            "## Datos y aserciones exactas por caso",
            "",
            "Las cadenas largas se incluyen completas en la colección; aquí se muestra el mismo contenido fuente.",
        ]
    )

    for caso in LISTA_CASOS_PRUEBA:
        lineas_matriz.extend(
            [
                "",
                f"### {caso['id']} — {caso['title']}",
                "",
                "```json",
                json.dumps(caso["steps"], ensure_ascii=False, indent=2),
                "```",
            ]
        )

    (DIRECTORIO_DOCUMENTACION / "MATRIZ_CASOS.md").write_text(
        "\n".join(lineas_matriz) + "\n", encoding="utf-8"
    )

    # 7. Ejecutar script de Bruno externo
    generar_bruno()
    print(
        f"Generados {len(LISTA_CASOS_PRUEBA)} casos y {len(solicitudes_thunder)} peticiones. Fechas de referencia UTC: {FECHA_ACTUAL}."
    )


if __name__ == "__main__":
    main()
