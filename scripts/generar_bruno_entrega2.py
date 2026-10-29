"""Convierte el manifiesto de QA a una colección Bruno con aserciones.

Este script lee los casos de prueba y las variables de entorno locales desde la
carpeta de QA y genera una estructura completa de archivos de colección y aserciones
compatibles con Bruno.
"""

import json
from pathlib import Path

QA = Path(__file__).resolve().parents[1] / "qa" / "entrega2"


"""
Construye un bloque de configuración formateado para los archivos de Bruno.

@param name - Nombre del bloque (ej. 'meta', 'vars', 'get', 'tests').
@param content - Texto interno que irá dentro del bloque.
@returns El bloque completo formateado en formato de texto estructurado.
"""


def block(name: str, content: str) -> str:
    return (
        name
        + " {\n"
        + "\n".join("  " + line for line in content.splitlines())
        + "\n}\n"
    )


"""
Función principal para la generación de la colección Bruno.

@param - No recibe parámetros de entrada directos.
@returns None - No retorna valores, genera archivos físicos en el disco.
"""


def main() -> None:
    cases = json.loads((QA / "casos.json").read_text(encoding="utf-8"))["cases"]
    env = json.loads(
        (QA / "thunder-environment_local.json").read_text(encoding="utf-8")
    )["variables"]
    root = QA / "bruno"
    (root / "environments").mkdir(parents=True, exist_ok=True)
    (root / "bruno.json").write_text(
        json.dumps(
            {
                "version": "1",
                "name": "Poki Koa - Entrega 2",
                "type": "collection",
                "ignore": ["node_modules", ".git"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "environments" / "Local.bru").write_text(
        block("vars", "\n".join(f"{v['name']}: {v['value']}" for v in env)),
        encoding="utf-8",
    )
    count = 0
    for case in cases:
        for index, item in enumerate(case["steps"]):
            count += 1
            label = case["id"] + (f".v{index}" if index else "")
            text = block(
                "meta", f"name: {label}\n{case['title']}\ntype: http\nseq: {count}"
            )
            text += "\n" + block(
                item["method"].lower(),
                f"url: {{{{base_url}}}}{item['path']}\nbody: {'json' if 'body' in item else 'none'}\nauth: none",
            )
            text += "\n" + block("headers", "Content-Type: application/json")
            if "body" in item:
                text += "\n" + block(
                    "body:json", json.dumps(item["body"], ensure_ascii=False, indent=2)
                )
            assertions = [
                f'test("HTTP {item["status"]}", () => expect(res.getStatus()).to.equal({item["status"]}));'
            ]
            for path, value in item.get("equals", {}).items():
                access = "res.getBody()" + "".join(
                    f"[{json.dumps(p)}]" for p in path.split(".")
                )
                expected = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and "{{" in value:
                    expected = f"bru.interpolate({expected})"
                assertions.append(
                    f"test({json.dumps('Valor ' + path)}, () => expect({access}).to.deep.equal({expected}));"
                )
            for key in item.get("keys", []):
                assertions.append(
                    f"test({json.dumps('Error ' + key)}, () => {{ expect(res.getBody()).to.have.property({json.dumps(key)}); expect(res.getBody()[{json.dumps(key)}]).to.not.be.empty; }});"
                )
            if "length" in item:
                assertions.append(
                    f'test("Cantidad persistida", () => {{ expect(res.getBody()).to.be.an("array"); expect(res.getBody()).to.have.lengthOf({item["length"]}); }});'
                )
            if item["status"] == 204:
                assertions.append(
                    'test("Sin cuerpo", () => expect(["", null, undefined]).to.include(res.getBody()));'
                )
            text += "\n" + block("tests", "\n".join(assertions))
            text += "\n" + block(
                "docs",
                f"{case['hu']} / {case['ca']}\n{case['technique']}\nCaso {case['id']}, paso {index + 1}. Ejecutar toda la colección en orden sobre la base restablecida.",
            )
            (root / f"{count:03}-{label}.bru").write_text(text, encoding="utf-8")
    print(f"Bruno: {len(cases)} casos, {count} solicitudes con aserciones.")


if __name__ == "__main__":
    main()
