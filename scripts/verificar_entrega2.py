"""Valida artefactos o ejecuta los casos contra un servidor aislado creado por el script.

python scripts/verificar_entrega2.py --static
uv run python scripts/verificar_entrega2.py --run
No acepta servidores externos: siempre utiliza settings_entregable y datos ficticios.
"""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Directorios raíz y de QA base para la verificación
DIRECTORIO_RAIZ = Path(__file__).resolve().parents[1]
DIRECTORIO_QA = DIRECTORIO_RAIZ / "qa" / "entrega2"


"""
Lee y deserializa un archivo en formato JSON desde la carpeta de QA.

@param nombre_archivo - Nombre o ruta relativa del archivo JSON a leer.
@returns dict | list - El contenido estructurado parseado del archivo.
"""


def leer_archivo_json(nombre_archivo: str) -> dict | list:
    return json.loads((DIRECTORIO_QA / nombre_archivo).read_text(encoding="utf-8"))


"""
Sustituye de forma recursiva las variables de plantilla por sus valores reales.

@param valor - Valor, cadena, diccionario o lista a procesar.
@param variables - Diccionario con los pares clave-valor de sustitución.
@returns any - La estructura con las variables resueltas.
"""


def sustituir_variables(valor: any, variables: dict) -> any:
    if isinstance(valor, str):
        for clave, reemplazo in variables.items():
            valor = valor.replace("{{" + clave + "}}", reemplazo)
        if "{{" in valor:
            raise ValueError(f"Variable no resuelta: {valor}")
        return valor
    if isinstance(valor, dict):
        return {
            clave: sustituir_variables(item, variables) for clave, item in valor.items()
        }
    if isinstance(valor, list):
        return [sustituir_variables(item, variables) for item in valor]
    return valor


"""
Busca de forma anidada un valor dentro de un objeto JSON usando notación de puntos.

@param cuerpo - Objeto de datos (diccionario o lista) sobre el cual buscar.
@param ruta - Ruta de claves separadas por puntos (ej. 'usuario.nombre').
@returns any - El valor encontrado en la ruta especificada.
"""


def buscar_en_json(cuerpo: any, ruta: str) -> any:
    for parte in ruta.split("."):
        cuerpo = cuerpo[int(parte)] if isinstance(cuerpo, list) else cuerpo[parte]
    return cuerpo


"""
Valida una respuesta HTTP contra las expectativas definidas en el caso de prueba.

@param codigo_estado - Código de estado HTTP obtenido en la respuesta.
@param cuerpo_respuesta - Cuerpo de la respuesta JSON o texto decodificado.
@param esperado - Diccionario con las reglas y aserciones esperadas.
@returns None - Lanza AssertionError si alguna regla de validación falla.
"""


def verificar_expectativa(
    codigo_estado: int, cuerpo_respuesta: any, esperado: dict
) -> None:
    if codigo_estado != esperado["status"]:
        raise AssertionError(
            f"HTTP esperado {esperado['status']}; obtenido {codigo_estado}: {cuerpo_respuesta}"
        )
    for ruta, valor in esperado.get("equals", {}).items():
        actual = buscar_en_json(cuerpo_respuesta, ruta)
        if actual != valor or (isinstance(valor, bool) and type(actual) is not bool):
            raise AssertionError(f"{ruta}: esperado {valor!r}; obtenido {actual!r}")
    for llave in esperado.get("keys", []):
        if (
            not isinstance(cuerpo_respuesta, dict)
            or llave not in cuerpo_respuesta
            or not cuerpo_respuesta[llave]
        ):
            raise AssertionError(f"Falta error no vacío en {llave}: {cuerpo_respuesta}")
    if "length" in esperado and (
        not isinstance(cuerpo_respuesta, list)
        or len(cuerpo_respuesta) != esperado["length"]
    ):
        raise AssertionError(
            f"Lista esperada de {esperado['length']} elementos; obtenido {cuerpo_respuesta}"
        )
    if codigo_estado == 204 and cuerpo_respuesta is not None:
        raise AssertionError("DELETE 204 debe responder sin cuerpo")


"""
Realiza una petición HTTP real utilizando la librería estándar de Python.

@param url_base - URL base del servidor de pruebas.
@param item - Diccionario con los detalles de la solicitud (método, ruta, cuerpo).
@returns tuple - Una tupla conteniendo el código de estado HTTP y el cuerpo JSON deserializado.
"""


def realizar_peticion_http(url_base: str, item: dict) -> tuple[int, any]:
    carga_util = json.dumps(item["body"]).encode() if "body" in item else None
    solicitud = Request(
        url_base + item["path"],
        data=carga_util,
        method=item["method"],
        headers={"Content-Type": "application/json"},
    )
    try:
        respuesta = urlopen(solicitud, timeout=10)
    except HTTPError as error:
        respuesta = error
    with respuesta:
        crudo = respuesta.read().decode()
        return respuesta.status, json.loads(crudo) if crudo else None


"""
Ejecuta la validación estática de todos los artefactos generados de la Entrega 2.

@param - No recibe parámetros directos.
@returns tuple - Una tupla con la lista de casos de prueba y el diccionario de entorno.
"""


def validate() -> tuple[list, dict]:
    casos = leer_archivo_json("casos.json")["cases"]
    coleccion = leer_archivo_json("thunder-collection_entrega2.json")
    entorno = {
        item["name"]: item["value"]
        for item in leer_archivo_json("thunder-environment_local.json")["variables"]
    }

    assert len(casos) == 44
    assert len({case["id"] for case in casos}) == len(casos)
    assert sum(case["hu"] == "US-01" for case in casos) == 22
    assert sum(case["hu"] == "US-02" for case in casos) == 22

    pasos = [paso for case in casos for paso in case["steps"]]
    assert len(pasos) == len(coleccion["requests"])

    identificadores = [request["_id"] for request in coleccion["requests"]]
    assert len(identificadores) == len(set(identificadores))

    carpetas = {folder["_id"] for folder in coleccion["folders"]}
    for item, request in zip(pasos, coleccion["requests"]):
        assert request["containerId"] in carpetas
        assert request["method"] == item["method"]
        assert request["url"] == "{{base_url}}" + item["path"]
        assert request["tests"][0]["value"] == str(item["status"])
        if "body" in item:
            assert json.loads(request["body"]["raw"]) == item["body"]
        assert len(request["tests"]) == 1 + len(item.get("equals", {})) + len(
            item.get("keys", [])
        ) + int("length" in item)
        sustituir_variables(item, entorno)

    fixtures = leer_archivo_json("datos_demo.json")
    llaves_fixtures = {(record["model"], record["pk"]) for record in fixtures}
    assert len(llaves_fixtures) == len(fixtures) == 10

    for record in fixtures:
        campos = record["fields"]
        if "paciente" in campos:
            assert ("cunas.bebe", campos["paciente"]) in llaves_fixtures
        if "medico_a_cargo" in campos:
            assert ("cunas.medico", campos["medico_a_cargo"]) in llaves_fixtures

    # Verifica que el evaluador detecte errores HTTP, de contenido y de persistencia.
    verificar_expectativa(200, {"peso": 3.2}, {"status": 200, "equals": {"peso": 3.2}})
    for status, cuerpo, esperado in [
        (201, {}, {"status": 400}),
        (200, {"peso": 0}, {"status": 200, "equals": {"peso": 3.2}}),
        (200, [{}], {"status": 200, "length": 0}),
        (400, {}, {"status": 400, "keys": ["peso"]}),
    ]:
        try:
            verificar_expectativa(status, cuerpo, esperado)
        except AssertionError:
            pass
        else:
            raise AssertionError("El evaluador aceptó una respuesta incorrecta")

    print(
        f"Validación estática OK: {len(casos)} casos, {len(pasos)} peticiones y {len(fixtures)} registros ficticios."
    )
    return casos, entorno


"""
Prepara el entorno, levanta un servidor de pruebas aislado y ejecuta todos los casos de QA.

@param - No recibe parámetros directos.
@returns int - Código de salida (0 si todo pasa, distinto de cero si hay fallos).
"""


def run() -> int:
    # Regenerar fechas antes de preparar el escenario evita fechas futuras obsoletas.
    subprocess.run(
        [
            sys.executable,
            str(DIRECTORIO_RAIZ / "scripts" / "preparar_pruebas_entrega2.py"),
        ],
        check=True,
    )
    casos, entorno = validate()

    comando_manage = [sys.executable, str(DIRECTORIO_RAIZ / "src" / "manage.py")]
    opciones_settings = "--settings=poki_koa.settings_entregable"

    subprocess.run(
        comando_manage + ["migrate", opciones_settings, "--noinput"], check=True
    )
    subprocess.run(
        comando_manage + ["preparar_entregable", opciones_settings, "--reset"],
        check=True,
    )

    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        puerto = sonda.getsockname()[1]

    url_base = f"http://127.0.0.1:{puerto}"
    reporte = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "HTTP real; NO Thunder Client",
        "python": sys.version,
        "manifest_sha256": hashlib.sha256(
            (DIRECTORIO_QA / "casos.json").read_bytes()
        ).hexdigest(),
        "cases": [],
    }

    ruta_log = DIRECTORIO_QA / "servidor-local.log"
    with ruta_log.open("w", encoding="utf-8") as archivo_log:
        servidor = subprocess.Popen(
            comando_manage
            + ["runserver", f"127.0.0.1:{puerto}", opciones_settings, "--noreload"],
            stdout=archivo_log,
            stderr=archivo_log,
            env=os.environ.copy(),
        )
        try:
            for _ in range(100):
                if servidor.poll() is not None:
                    raise RuntimeError(f"El servidor terminó; revisar {ruta_log}")
                try:
                    status, cuerpo = realizar_peticion_http(
                        url_base, {"path": "/api/bebes/", "method": "GET"}
                    )
                    if status == 200:
                        break
                except (URLError, OSError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("El servidor no respondió dentro de 10 segundos")

            for case in casos:
                resultado_caso = {
                    "id": case["id"],
                    "title": case["title"],
                    "status": "PASS",
                    "steps": [],
                }
                for plantilla in case["steps"]:
                    item = sustituir_variables(plantilla, entorno)
                    detalle = {
                        "method": item["method"],
                        "path": item["path"],
                        "expected_status": item["status"],
                    }
                    try:
                        status, cuerpo = realizar_peticion_http(url_base, item)
                        detalle.update({"actual_status": status, "response": cuerpo})
                        verificar_expectativa(status, cuerpo, item)

                        # Cada alta válida se vuelve a consultar para verificar persistencia.
                        if item["method"] == "POST" and status == 201:
                            persistido = {
                                **item,
                                "method": "GET",
                                "path": item["path"] + str(cuerpo["id"]) + "/",
                                "status": 200,
                            }
                            persistido.pop("body", None)
                            estado_lectura, cuerpo_lectura = realizar_peticion_http(
                                url_base, persistido
                            )
                            verificar_expectativa(
                                estado_lectura, cuerpo_lectura, persistido
                            )
                            detalle["persisted_id"] = cuerpo["id"]
                    except (
                        AssertionError,
                        KeyError,
                        IndexError,
                        TypeError,
                        ValueError,
                        OSError,
                    ) as error:
                        resultado_caso["status"] = "FAIL"
                        detalle["error"] = str(error)
                    resultado_caso["steps"].append(detalle)
                reporte["cases"].append(resultado_caso)
                print(case["id"], resultado_caso["status"])
        finally:
            servidor.terminate()
            try:
                servidor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                servidor.kill()
                servidor.wait()

    reporte["passed"] = sum(case["status"] == "PASS" for case in reporte["cases"])
    reporte["failed"] = sum(case["status"] == "FAIL" for case in reporte["cases"])

    (DIRECTORIO_QA / "resultado-http-local.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"HTTP: {reporte['passed']} PASS / {reporte['failed']} FAIL. No acredita ejecución en Thunder Client."
    )
    return int(reporte["failed"] != 0)


if __name__ == "__main__":
    analizador_argumentos = argparse.ArgumentParser(description=__doc__)
    grupo_modo = analizador_argumentos.add_mutually_exclusive_group(required=True)
    grupo_modo.add_argument("--static", action="store_true")
    grupo_modo.add_argument("--run", action="store_true")
    argumentos = analizador_argumentos.parse_args()

    if argumentos.static:
        validate()
    else:
        sys.exit(run())
