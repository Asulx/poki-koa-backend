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

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "qa" / "entrega2"


def read(name):
    return json.loads((QA / name).read_text(encoding="utf-8"))


def substitute(value, variables):
    if isinstance(value, str):
        for key, replacement in variables.items():
            value = value.replace("{{" + key + "}}", replacement)
        if "{{" in value:
            raise ValueError(f"Variable no resuelta: {value}")
        return value
    if isinstance(value, dict):
        return {key: substitute(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, variables) for item in value]
    return value


def lookup(body, path):
    for part in path.split("."):
        body = body[int(part)] if isinstance(body, list) else body[part]
    return body


def check(status, body, expected):
    if status != expected["status"]:
        raise AssertionError(
            f"HTTP esperado {expected['status']}; obtenido {status}: {body}"
        )
    for path, value in expected.get("equals", {}).items():
        actual = lookup(body, path)
        if actual != value or (isinstance(value, bool) and type(actual) is not bool):
            raise AssertionError(f"{path}: esperado {value!r}; obtenido {actual!r}")
    for key in expected.get("keys", []):
        if not isinstance(body, dict) or key not in body or not body[key]:
            raise AssertionError(f"Falta error no vacío en {key}: {body}")
    if "length" in expected and (
        not isinstance(body, list) or len(body) != expected["length"]
    ):
        raise AssertionError(
            f"Lista esperada de {expected['length']} elementos; obtenido {body}"
        )
    if status == 204 and body is not None:
        raise AssertionError("DELETE 204 debe responder sin cuerpo")


def http(base, item):
    payload = json.dumps(item["body"]).encode() if "body" in item else None
    request = Request(
        base + item["path"],
        data=payload,
        method=item["method"],
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else None


def validate():
    cases = read("casos.json")["cases"]
    collection = read("thunder-collection_entrega2.json")
    env = {
        item["name"]: item["value"]
        for item in read("thunder-environment_local.json")["variables"]
    }
    assert len(cases) == 44
    assert len({case["id"] for case in cases}) == len(cases)
    assert sum(case["hu"] == "US-01" for case in cases) == 22
    assert sum(case["hu"] == "US-02" for case in cases) == 22
    steps = [step for case in cases for step in case["steps"]]
    assert len(steps) == len(collection["requests"])
    ids = [request["_id"] for request in collection["requests"]]
    assert len(ids) == len(set(ids))
    folders = {folder["_id"] for folder in collection["folders"]}
    for item, request in zip(steps, collection["requests"]):
        assert request["containerId"] in folders
        assert request["method"] == item["method"]
        assert request["url"] == "{{base_url}}" + item["path"]
        assert request["tests"][0]["value"] == str(item["status"])
        if "body" in item:
            assert json.loads(request["body"]["raw"]) == item["body"]
        assert len(request["tests"]) == 1 + len(item.get("equals", {})) + len(
            item.get("keys", [])
        ) + int("length" in item)
        substitute(item, env)
    fixtures = read("datos_demo.json")
    keys = {(record["model"], record["pk"]) for record in fixtures}
    assert len(keys) == len(fixtures) == 10
    for record in fixtures:
        fields = record["fields"]
        if "paciente" in fields:
            assert ("cunas.bebe", fields["paciente"]) in keys
        if "medico_a_cargo" in fields:
            assert ("cunas.medico", fields["medico_a_cargo"]) in keys
    # Verifica que el evaluador detecte errores HTTP, de contenido y de persistencia.
    check(200, {"peso": 3.2}, {"status": 200, "equals": {"peso": 3.2}})
    for status, body, expected in [
        (201, {}, {"status": 400}),
        (200, {"peso": 0}, {"status": 200, "equals": {"peso": 3.2}}),
        (200, [{}], {"status": 200, "length": 0}),
        (400, {}, {"status": 400, "keys": ["peso"]}),
    ]:
        try:
            check(status, body, expected)
        except AssertionError:
            pass
        else:
            raise AssertionError("El evaluador aceptó una respuesta incorrecta")
    print(
        f"Validación estática OK: {len(cases)} casos, {len(steps)} peticiones y {len(fixtures)} registros ficticios."
    )
    return cases, env


def run():
    # Regenerar fechas antes de preparar el escenario evita fechas futuras obsoletas.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "preparar_pruebas_entrega2.py")],
        check=True,
    )
    cases, env = validate()
    manage = [sys.executable, str(ROOT / "src" / "manage.py")]
    settings = "--settings=poki_koa.settings_entregable"
    subprocess.run(manage + ["migrate", settings, "--noinput"], check=True)
    subprocess.run(manage + ["preparar_entregable", settings, "--reset"], check=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": "HTTP real; NO Thunder Client",
        "python": sys.version,
        "manifest_sha256": hashlib.sha256((QA / "casos.json").read_bytes()).hexdigest(),
        "cases": [],
    }
    log_path = QA / "servidor-local.log"
    with log_path.open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            manage + ["runserver", f"127.0.0.1:{port}", settings, "--noreload"],
            stdout=log,
            stderr=log,
            env=os.environ.copy(),
        )
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError(f"El servidor terminó; revisar {log_path}")
                try:
                    status, body = http(base, {"path": "/api/bebes/", "method": "GET"})
                    if status == 200:
                        break
                except (URLError, OSError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("El servidor no respondió dentro de 10 segundos")
            for case in cases:
                result = {
                    "id": case["id"],
                    "title": case["title"],
                    "status": "PASS",
                    "steps": [],
                }
                for template in case["steps"]:
                    item = substitute(template, env)
                    detail = {
                        "method": item["method"],
                        "path": item["path"],
                        "expected_status": item["status"],
                    }
                    try:
                        status, body = http(base, item)
                        detail.update({"actual_status": status, "response": body})
                        check(status, body, item)
                        # Cada alta válida se vuelve a consultar para verificar persistencia.
                        if item["method"] == "POST" and status == 201:
                            persisted = {
                                **item,
                                "method": "GET",
                                "path": item["path"] + str(body["id"]) + "/",
                                "status": 200,
                            }
                            persisted.pop("body", None)
                            read_status, read_body = http(base, persisted)
                            check(read_status, read_body, persisted)
                            detail["persisted_id"] = body["id"]
                    except (
                        AssertionError,
                        KeyError,
                        IndexError,
                        TypeError,
                        ValueError,
                        OSError,
                    ) as error:
                        result["status"] = "FAIL"
                        detail["error"] = str(error)
                    result["steps"].append(detail)
                report["cases"].append(result)
                print(case["id"], result["status"])
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
    report["passed"] = sum(case["status"] == "PASS" for case in report["cases"])
    report["failed"] = sum(case["status"] == "FAIL" for case in report["cases"])
    (QA / "resultado-http-local.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"HTTP: {report['passed']} PASS / {report['failed']} FAIL. No acredita ejecución en Thunder Client."
    )
    return int(report["failed"] != 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--static", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.static:
        validate()
    else:
        sys.exit(run())
