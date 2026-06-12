"""
Ensamblado del "documento semántico" del programa: el contexto estructurado
que el Compilador Aumentado entrega a la capa de IA.

`serialize_program` combina las tres fuentes de verdad del compilador en un único
diccionario JSON-compatible:
  - AST decorado con tipos (vía JsonSerializer),
  - tabla de símbolos por función (parámetros + variables locales con su tipo y
    posición de declaración),
  - CFG por función (bloques básicos y aristas),
  - diagnósticos (errores semánticos con posición).

El LLM consume este documento — no el texto fuente — para responder consultas
ancladas en la semántica formal verificada por el compilador.
"""

from __future__ import annotations

from typing import List, Optional

from ..parser.ast_nodes import (
    Block, ForStmt, FunctionDecl, IfStmt, VarDecl, WhileStmt,
)
from ..cfg.blocks import ControlFlowGraph, _stmt_summary
from .json_serializer import JsonSerializer


def serialize_program(program, errors=None, cfgs=None) -> dict:
    """Construye el documento semántico completo del programa."""
    js = JsonSerializer()
    cfg_by_name = {c.function_name: c for c in (cfgs or [])}

    functions: List[dict] = []
    globals_: List[dict] = []
    for stmt in program.body:
        if isinstance(stmt, FunctionDecl):
            functions.append(_serialize_function(stmt, js, cfg_by_name.get(stmt.name)))
        elif isinstance(stmt, VarDecl):
            globals_.append(_decl_entry(stmt, scope="global"))

    return {
        "language": "MiniLang",
        "functions": functions,
        "globals": globals_,
        "diagnostics": [_diagnostic(e) for e in (errors or [])],
    }


# ─────────────────────────────────────────────────────────────────────────────

def _serialize_function(fn: FunctionDecl, js: JsonSerializer,
                        cfg: Optional[ControlFlowGraph]) -> dict:
    entry = {
        "name": fn.name,
        "return_type": fn.return_type,
        "line": fn.line, "column": fn.column,
        "params": [
            {"name": p.name, "type": p.type_name, "kind": "param",
             "line": p.line, "column": p.column}
            for p in fn.params
        ],
        "locals": _collect_locals(fn.body, scope=f"func:{fn.name}"),
        "ast": js.serialize(fn.body),
    }
    if cfg is not None:
        entry["cfg"] = _serialize_cfg(cfg)
    return entry


def _decl_entry(node: VarDecl, scope: str) -> dict:
    return {"name": node.name, "type": node.type_name, "kind": "var",
            "scope": scope, "line": node.line, "column": node.column}


def _collect_locals(node, scope: str) -> List[dict]:
    """Recorre el cuerpo de una función y reúne todas las variables declaradas."""
    out: List[dict] = []

    def walk(n, scope_label: str) -> None:
        if isinstance(n, Block):
            for s in n.body:
                walk(s, scope_label)
        elif isinstance(n, VarDecl):
            out.append(_decl_entry(n, scope_label))
        elif isinstance(n, IfStmt):
            walk(n.then_branch, scope_label)
            if n.else_branch is not None:
                walk(n.else_branch, scope_label)
        elif isinstance(n, WhileStmt):
            walk(n.body, scope_label)
        elif isinstance(n, ForStmt):
            if n.init is not None:
                walk(n.init, f"{scope_label}/for")
            walk(n.body, f"{scope_label}/for")

    walk(node, scope)
    return out


def _serialize_cfg(cfg: ControlFlowGraph) -> dict:
    return {
        "entry": cfg.entry.id if cfg.entry else None,
        "exit": cfg.exit.id if cfg.exit else None,
        "blocks": [
            {
                "id": b.id,
                "label": b.label,
                "condition": _stmt_summary(b.condition) if b.condition else None,
                "statements": [_stmt_summary(s) for s in b.statements],
                "successors": [
                    {"to": e.target.id, "label": e.label} for e in b.successors
                ],
            }
            for b in cfg.blocks
        ],
    }


def _diagnostic(err) -> dict:
    return {
        "phase": "semantic",
        "message": err.args[0],
        "line": getattr(err, "line", 0),
        "column": getattr(err, "column", 0),
    }
