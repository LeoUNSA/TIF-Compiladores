"""
Selección de contexto: extrae del documento semántico la porción relevante para
cada consulta, de modo que el prompt enviado al LLM sea compacto y enfocado.

Todas las funciones operan sobre el dict producido por `serialize.serialize_program`.
"""

from __future__ import annotations

from typing import List, Optional


def find_function(doc: dict, name: str) -> Optional[dict]:
    return next((f for f in doc["functions"] if f["name"] == name), None)


def find_variable(doc: dict, name: str) -> List[dict]:
    """Todas las apariciones de una variable/parámetro/global con ese nombre."""
    hits: List[dict] = []
    for f in doc["functions"]:
        for p in f["params"]:
            if p["name"] == name:
                hits.append({"funcion": f["name"], **p})
        for l in f["locals"]:
            if l["name"] == name:
                init = _find_initializer(f["ast"], name)
                entry = {"funcion": f["name"], **l}
                if init is not None:
                    entry["inicializador"] = init
                hits.append(entry)
    for g in doc["globals"]:
        if g["name"] == name:
            hits.append({"funcion": None, **g})
    return hits


def structure(doc: dict) -> dict:
    """Resumen estructural del programa (para --navigate)."""
    funcs = []
    for f in doc["functions"]:
        blocks = f.get("cfg", {}).get("blocks", [])
        loops = sum(1 for b in blocks if b["label"] in ("while.cond", "for.cond"))
        branches = sum(1 for b in blocks if b["label"] == "if.then")
        funcs.append({
            "nombre": f["name"],
            "tipo_retorno": f["return_type"],
            "parametros": [f"{p['type']} {p['name']}" for p in f["params"]],
            "variables_locales": [l["name"] for l in f["locals"]],
            "bloques_cfg": len(blocks),
            "bucles": loops,
            "ramas_if": branches,
        })
    return {"funciones": funcs, "globales": doc["globals"]}


def diagnostics_with_source(doc: dict, source: str) -> dict:
    """Diagnósticos del compilador junto a las líneas de fuente referenciadas."""
    lines = source.splitlines()
    diags = []
    for d in doc["diagnostics"]:
        ln = d.get("line", 0)
        snippet = lines[ln - 1] if 1 <= ln <= len(lines) else ""
        diags.append({**d, "codigo": snippet.strip()})
    return {"diagnosticos": diags}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_initializer(node, name: str):
    """Busca el inicializador del VarDecl de `name` dentro de un AST serializado."""
    if isinstance(node, dict):
        if node.get("node") == "VarDecl" and node.get("name") == name:
            return node.get("initializer")
        for v in node.values():
            r = _find_initializer(v, name)
            if r is not None:
                return r
    elif isinstance(node, list):
        for it in node:
            r = _find_initializer(it, name)
            if r is not None:
                return r
    return None
