"""Genera casos, colecciones y matriz desde una única definición; no necesita Django."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from generar_bruno_entrega2 import main as generar_bruno

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa" / "entrega2"
DOC = ROOT / "docs" / "entrega2"
NOW = datetime.now(timezone.utc)
STAMP = NOW.isoformat()
TODAY = NOW.date()
ENV = {
    "base_url": "http://127.0.0.1:8000",
    "ayer": str(TODAY - timedelta(days=1)),
    "hoy": str(TODAY),
    "manana": str(TODAY + timedelta(days=1)),
}
CASES = []


def dump(path, obj):
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def step(method, path, status, body=None, equals=None, keys=None, length=None):
    result = {"method": method, "path": path, "status": status}
    if body is not None:
        result["body"] = body
    if equals:
        result["equals"] = equals
    if keys:
        result["keys"] = keys
    if length is not None:
        result["length"] = length
    return result


def add(id_, title, ca, technique, request, verifies=None):
    CASES.append(
        {
            "id": id_,
            "title": title,
            "hu": "US-01" if id_[0] == "B" else "US-02",
            "ca": ca,
            "technique": technique,
            "steps": [request] + (verifies or []),
        }
    )


def baby(n, title, ca, technique, changes=None, omit=(), error=None):
    id_ = f"B{n:02}"
    body = {
        "identificador": f"QA-{id_}",
        "nombre_completo": "Paciente ficticio QA",
        "edad_meses": 0,
        "sexo": "F",
        "peso": 3.2,
        "fecha_nacimiento": "{{ayer}}",
        "medico_a_cargo": 910001,
    }
    body.update(changes or {})
    for field in omit:
        body.pop(field)
    equals = None if error else {k: v for k, v in body.items()}
    verifies = []
    # Cada alta rechazada con identificador propio comprueba ausencia de escritura.
    if error and body.get("identificador") == f"QA-{id_}":
        verifies.append(
            step("GET", f"/api/bebes/?identificador=QA-{id_}", 200, length=0)
        )
    add(
        id_,
        title,
        ca,
        technique,
        step(
            "POST",
            "/api/bebes/",
            400 if error else 201,
            body,
            equals,
            [error] if error else None,
        ),
        verifies,
    )


baby(
    1,
    "Registro válido con médico existente",
    "B-CA1,B-CA4",
    "Equivalencia válida / negocio",
)
baby(
    2,
    "Identificador obligatorio ausente",
    "B-CA2",
    "Equivalencia inválida",
    omit=("identificador",),
    error="identificador",
)
baby(
    3,
    "Identificador ya registrado",
    "B-CA2",
    "Negocio: unicidad",
    {"identificador": "QA-BASE-1"},
    error="identificador",
)
baby(
    4,
    "Nombre vacío",
    "B-CA2",
    "Equivalencia inválida",
    {"nombre_completo": ""},
    error="nombre_completo",
)
for n, size in [(5, 199), (6, 200), (7, 201)]:
    baby(
        n,
        f"Nombre de {size} caracteres",
        "B-CA2",
        "Límite superior de longitud",
        {"nombre_completo": "N" * size},
        error="nombre_completo" if size > 200 else None,
    )
baby(
    8,
    "Peso no numérico",
    "B-CA3",
    "Equivalencia inválida: tipo",
    {"peso": "abc"},
    error="peso",
)
for n, weight in [(9, -0.01), (10, 0), (11, 0.01)]:
    baby(
        n,
        f"Peso {weight}",
        "B-CA3",
        "Límite inferior: peso > 0",
        {"peso": weight},
        error="peso" if weight <= 0 else None,
    )
baby(
    12,
    "Peso y fecha opcionales nulos",
    "B-CA3",
    "Equivalencia válida: ausencia opcional",
    {"peso": None, "fecha_nacimiento": None},
)
for n, date in [(13, "ayer"), (14, "hoy"), (15, "manana")]:
    baby(
        n,
        f"Fecha de nacimiento: {date}",
        "B-CA3",
        "Límite temporal",
        {"fecha_nacimiento": "{{" + date + "}}"},
        error="fecha_nacimiento" if date == "manana" else None,
    )
baby(
    16,
    "Sexo fuera del catálogo",
    "B-CA2",
    "Equivalencia inválida: elección",
    {"sexo": "X"},
    error="sexo",
)
baby(
    17,
    "Médico inexistente",
    "B-CA4",
    "Negocio: integridad referencial",
    {"medico_a_cargo": 999999},
    error="medico_a_cargo",
)
add(
    "B18",
    "Modificar diagnóstico sin perder otros datos",
    "B-CA5",
    "Negocio: actualización parcial",
    step(
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
        step(
            "GET",
            "/api/bebes/910001/",
            200,
            equals={
                "diagnostico": "Observación QA actualizada",
                "peso": 3.2,
                "medico_a_cargo": 910001,
            },
        )
    ],
)
add(
    "B19",
    "Edición inválida no guarda ni siquiera los campos válidos",
    "B-CA3,B-CA5",
    "Negocio: rechazo atómico",
    step(
        "PATCH",
        "/api/bebes/910001/",
        400,
        {"peso": 0, "diagnostico": "NO DEBE GUARDARSE"},
        keys=["peso"],
    ),
    [
        step(
            "GET",
            "/api/bebes/910001/",
            200,
            equals={"peso": 3.2, "diagnostico": "Observación QA actualizada"},
        )
    ],
)
add(
    "B20",
    "Consultar paciente inexistente",
    "B-CA5",
    "Equivalencia inválida: recurso",
    step("GET", "/api/bebes/999999/", 404, keys=["detail"]),
)
add(
    "B21",
    "Recuperar datos para edición y relaciones",
    "B-CA5",
    "Negocio: precarga de edición",
    step(
        "GET",
        "/api/bebes/910001/",
        200,
        equals={
            "identificador": "QA-BASE-1",
            "medico_nombre": "Profesional ficticio QA",
            "cuna": "QA-CUNA-1",
            "medicamentos.0.id": 910001,
        },
    ),
)
add(
    "B22",
    "Eliminar paciente libera cuna y elimina medicación asociada",
    "B-CA6",
    "Negocio: cascada y SET_NULL (alcance adicional)",
    step("DELETE", "/api/bebes/910003/", 204),
    [
        step("GET", "/api/bebes/910003/", 404, keys=["detail"]),
        step("GET", "/api/medicamentos/910003/", 404, keys=["detail"]),
        step("GET", "/api/cunas/910002/", 200, equals={"paciente": None}),
    ],
)


CATALOG = "/api/catalogo-medicamentos/"


def catalog(n, title, technique, changes=None, omit=(), error=None):
    body = {
        "nombre": f"Producto ficticio M{n:02}",
        "principio_activo": "Sustancia QA",
        "dosis_mg": "1.00",
        "stock": 10,
    }
    body.update(changes or {})
    for key in omit:
        body.pop(key)
    add(
        f"M{n:02}",
        title,
        "M-CA1,M-CA3",
        technique,
        step(
            "POST",
            CATALOG,
            400 if error else 201,
            body,
            equals=None if error else body,
            keys=[error] if error else None,
        ),
    )


catalog(1, "Registro válido en catálogo", "Equivalencia válida")
catalog(
    2, "Nombre obligatorio", "Equivalencia inválida", omit=("nombre",), error="nombre"
)
catalog(
    3,
    "Principio activo vacío",
    "Equivalencia inválida",
    {"principio_activo": " "},
    error="principio_activo",
)
catalog(4, "Nombre de 150 caracteres", "Límite superior", {"nombre": "N" * 150})
catalog(
    5,
    "Nombre de 151 caracteres",
    "Límite excedido",
    {"nombre": "N" * 151},
    error="nombre",
)
catalog(
    6,
    "Principio activo de 150 caracteres",
    "Límite superior",
    {"principio_activo": "P" * 150},
)
catalog(
    7,
    "Principio activo de 151 caracteres",
    "Límite excedido",
    {"principio_activo": "P" * 151},
    error="principio_activo",
)
catalog(
    8,
    "Dosis no numérica",
    "Equivalencia inválida",
    {"dosis_mg": "abc"},
    error="dosis_mg",
)
catalog(
    9, "Dosis cero", "Límite inferior excluido", {"dosis_mg": "0.00"}, error="dosis_mg"
)
catalog(10, "Dosis mínima 0.01 mg", "Límite inferior incluido", {"dosis_mg": "0.01"})
catalog(
    11,
    "Dosis con exceso de decimales",
    "Precisión decimal",
    {"dosis_mg": "0.001"},
    error="dosis_mg",
)
catalog(12, "Stock cero", "Límite inferior excluido", {"stock": 0}, error="stock")
catalog(13, "Stock mínimo una unidad", "Límite inferior incluido", {"stock": 1})
catalog(
    14, "Stock fraccionario", "Equivalencia inválida", {"stock": 1.5}, error="stock"
)
catalog(
    15, "Stock obligatorio", "Equivalencia inválida", omit=("stock",), error="stock"
)
catalog(
    16,
    "Dosis obligatoria",
    "Equivalencia inválida",
    omit=("dosis_mg",),
    error="dosis_mg",
)
add(
    "M17",
    "Consulta para precarga",
    "M-CA2",
    "Negocio: recuperar producto",
    step(
        "GET",
        CATALOG + "910001/",
        200,
        equals={
            "nombre": "Producto base QA",
            "principio_activo": "Sustancia QA",
            "dosis_mg": "1.00",
            "stock": 10,
        },
    ),
)
add(
    "M18",
    "Modificar stock y conservar otros campos",
    "M-CA2",
    "Negocio: persistencia",
    step(
        "PATCH",
        CATALOG + "910001/",
        200,
        {"stock": 5},
        {"stock": 5, "dosis_mg": "1.00"},
    ),
    [
        step(
            "GET",
            CATALOG + "910001/",
            200,
            equals={"stock": 5, "nombre": "Producto base QA"},
        )
    ],
)
add(
    "M19",
    "Edición inválida no guarda cambios parciales",
    "M-CA2,M-CA3",
    "Negocio: rechazo atómico",
    step(
        "PATCH",
        CATALOG + "910001/",
        400,
        {"stock": -1, "nombre": "NO GUARDAR"},
        keys=["stock"],
    ),
    [
        step(
            "GET",
            CATALOG + "910001/",
            200,
            equals={"stock": 5, "nombre": "Producto base QA"},
        )
    ],
)
add(
    "M20",
    "Producto inexistente",
    "M-CA2",
    "Equivalencia inválida",
    step("GET", CATALOG + "999999/", 404, keys=["detail"]),
)
add(
    "M21",
    "Modificar todos los campos",
    "M-CA2",
    "Negocio: actualización completa",
    step(
        "PUT",
        CATALOG + "910001/",
        200,
        {
            "nombre": "Producto actualizado QA",
            "principio_activo": "Sustancia nueva QA",
            "dosis_mg": "2.50",
            "stock": 20,
        },
    ),
    [
        step(
            "GET",
            CATALOG + "910001/",
            200,
            equals={
                "nombre": "Producto actualizado QA",
                "principio_activo": "Sustancia nueva QA",
                "dosis_mg": "2.50",
                "stock": 20,
            },
        )
    ],
)
add(
    "M22",
    "PUT incompleto conserva el producto",
    "M-CA2,M-CA3",
    "Negocio: campos requeridos",
    step(
        "PUT",
        CATALOG + "910001/",
        400,
        {"nombre": "NO GUARDAR"},
        keys=["principio_activo", "dosis_mg", "stock"],
    ),
    [
        step(
            "GET",
            CATALOG + "910001/",
            200,
            equals={"nombre": "Producto actualizado QA", "stock": 20},
        )
    ],
)

counts = {"B": 3, "M": 1}
for case in CASES:
    first = case["steps"][0]
    if first["method"] == "POST":
        group = case["id"][0]
        counts[group] += int(first["status"] == 201)
        case["steps"].append(step("GET", first["path"], 200, length=counts[group]))


def uid(value):
    return str(uuid5(NAMESPACE_URL, "poki-koa/entrega2/" + value))


def text_value(value):
    return value if isinstance(value, str) else json.dumps(value)


def tc_request(case, item, index, order):
    name = case["id"] + (f".v{index}" if index else "") + " — " + case["title"]
    tests = [
        {
            "type": "res-code",
            "custom": "",
            "action": "equal",
            "value": str(item["status"]),
        }
    ]
    for key, value in item.get("equals", {}).items():
        query = re.sub(r"\.(\d+)(?=\.|$)", r"[\1]", "json." + key)
        tests.append(
            {
                "type": "json",
                "custom": query,
                "action": "equal",
                "value": text_value(value),
            }
        )
    for key in item.get("keys", []):
        tests.append(
            {"type": "json", "custom": "json." + key, "action": "exists", "value": ""}
        )
    if "length" in item:
        tests.append(
            {
                "type": "json",
                "custom": "json",
                "action": "count",
                "value": str(item["length"]),
            }
        )
    request = {
        "_id": uid(name),
        "colId": uid("collection"),
        "containerId": uid(case["hu"]),
        "name": name,
        "url": "{{base_url}}" + item["path"],
        "method": item["method"],
        "sortNum": order * 10000,
        "created": STAMP,
        "modified": STAMP,
        "headers": [{"name": "Content-Type", "value": "application/json"}],
        "params": [],
        "tests": tests,
        "description": f"{case['ca']} | {case['technique']}. Ejecutar en orden; ver docs/entrega2.",
    }
    if "body" in item:
        request["body"] = {
            "type": "json",
            "raw": json.dumps(item["body"], ensure_ascii=False, indent=2),
            "form": [],
        }
    return request


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    dump(OUT / "casos.json", {"schema": 1, "cases": CASES})
    requests = []
    http = [f"@{key} = {value}" for key, value in ENV.items()]
    for case in CASES:
        for index, item in enumerate(case["steps"]):
            requests.append(tc_request(case, item, index, len(requests) + 1))
            http.extend(
                [
                    "",
                    f"### {case['id']} paso {index + 1}: {case['title']}",
                    f"# Esperado: HTTP {item['status']}; {json.dumps({k: v for k, v in item.items() if k in ('equals', 'keys', 'length')}, ensure_ascii=False)}",
                    f"{item['method']} {{{{base_url}}}}{item['path']}",
                    "Content-Type: application/json",
                    "",
                ]
            )
            if "body" in item:
                http.append(json.dumps(item["body"], ensure_ascii=False, indent=2))
    dump(
        OUT / "thunder-collection_entrega2.json",
        {
            "client": "Thunder Client",
            "collectionName": "Poki Koa — Entrega 2 — 44 casos",
            "dateExported": STAMP,
            "version": "1.1",
            "folders": [
                {
                    "_id": uid(hu),
                    "name": hu,
                    "containerId": "",
                    "created": STAMP,
                    "sortNum": n * 10000,
                }
                for n, hu in enumerate(["US-01", "US-02"], 1)
            ],
            "requests": requests,
        },
    )
    dump(
        OUT / "thunder-environment_local.json",
        {
            "client": "Thunder Client",
            "environmentName": "Poki Koa — Demo local",
            "dateExported": STAMP,
            "version": "1.0",
            "variables": [{"name": k, "value": v} for k, v in ENV.items()],
        },
    )
    (OUT / "peticiones.http").write_text("\n".join(http) + "\n", encoding="utf-8")
    fixtures = [
        {
            "model": "cunas.medico",
            "pk": 910001,
            "fields": {"nombre_completo": "Profesional ficticio QA", "turno": "Prueba"},
        }
    ]
    for pk, label in [(910001, "uno"), (910002, "dos"), (910003, "tres")]:
        fixtures.append(
            {
                "model": "cunas.bebe",
                "pk": pk,
                "fields": {
                    "identificador": f"QA-BASE-{pk - 910000}",
                    "nombre_completo": f"Paciente base {label} QA",
                    "edad_meses": 0,
                    "sexo": "F",
                    "peso": 3.2,
                    "medico_a_cargo": 910001,
                    "fecha_nacimiento": str(TODAY - timedelta(days=1)),
                    "fecha_ingreso": STAMP,
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
    for pk, patient in [(910001, 910001), (910002, 910003)]:
        fixtures.append(
            {
                "model": "cunas.cuna",
                "pk": pk,
                "fields": {
                    "identificador": f"QA-CUNA-{pk - 910000}",
                    "paciente": patient,
                    "ritmo_cardiaco": 130,
                    "spo2": 98,
                    "temperatura": 36.8,
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": False,
                    "ultima_actualizacion": STAMP,
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
    dump(OUT / "datos_demo.json", fixtures)
    lines = [
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
    for case in CASES:
        s = case["steps"][0]
        lines.append(
            f"| {case['id']} | {case['hu']} / {case['ca']} | {case['title']} | {case['technique']} | `{s['method']} {s['path']}` | {s['status']}; comprobar cuerpo y pasos posteriores |"
        )
    lines.extend(
        [
            "",
            "## Datos y aserciones exactas por caso",
            "",
            "Las cadenas largas se incluyen completas en la colección; aquí se muestra el mismo contenido fuente.",
        ]
    )
    for case in CASES:
        lines.extend(
            [
                "",
                f"### {case['id']} — {case['title']}",
                "",
                "```json",
                json.dumps(case["steps"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
    (DOC / "MATRIZ_CASOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    generar_bruno()
    print(
        f"Generados {len(CASES)} casos y {len(requests)} peticiones. Fechas de referencia UTC: {TODAY}."
    )


if __name__ == "__main__":
    main()
