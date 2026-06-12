"""
Estructuras del Grafo de Flujo de Control (CFG) de MiniLang.

Un CFG modela el flujo de ejecución de una función como un grafo dirigido de
**bloques básicos**: secuencias máximas de sentencias de flujo lineal (sin saltos
internos) conectadas por **aristas** que representan las posibles transferencias
de control (saltos condicionales, retornos de bucle, break/continue, return).

Es la última de las "fuentes de verdad" del compilador (junto al AST decorado y la
tabla de símbolos) que el Compilador Aumentado expone a la capa de IA para explicar
el flujo de un programa de forma accesible (`--navigate`, explicación de bucles, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..parser.ast_nodes import Expression, Statement


@dataclass
class Edge:
    """Arista dirigida entre dos bloques, con etiqueta opcional ('true'/'false'/'')."""
    target: "BasicBlock"
    label:  str = ""


@dataclass
class BasicBlock:
    """Bloque básico: secuencia de sentencias y sus aristas de salida."""
    id:    int
    label: str                                   # "entry", "if.then", "while.cond"...
    statements: List[Statement] = field(default_factory=list)
    successors: List[Edge] = field(default_factory=list)
    # Expresión de control si el bloque termina en una decisión (if/while/for):
    condition: Optional[Expression] = None

    @property
    def name(self) -> str:
        return f"B{self.id}({self.label})"


class ControlFlowGraph:
    """CFG de una función: bloques, entrada y salida (sink) únicas."""

    def __init__(self, function_name: str) -> None:
        self.function_name = function_name
        self.blocks: List[BasicBlock] = []
        self._counter = 0
        self.entry: Optional[BasicBlock] = None
        self.exit:  Optional[BasicBlock] = None

    def new_block(self, label: str) -> BasicBlock:
        block = BasicBlock(id=self._counter, label=label)
        self._counter += 1
        self.blocks.append(block)
        return block

    @staticmethod
    def connect(src: BasicBlock, dst: BasicBlock, label: str = "") -> None:
        src.successors.append(Edge(target=dst, label=label))


# ─────────────────────────────────────────────────────────────────────────────
# Formateo accesible (texto lineal, apto para lector de pantalla y capa de IA)
# ─────────────────────────────────────────────────────────────────────────────

def _stmt_summary(node) -> str:
    """Resumen corto de una sentencia/expresión para listar dentro de un bloque."""
    cls = type(node).__name__
    name = getattr(node, "name", None)
    type_name = getattr(node, "type_name", None)
    op = getattr(node, "operator", None)
    if type_name and name:                       # VarDecl
        return f"{cls} {type_name} {name}"
    if op and name:                              # AssignExpr
        return f"{cls} {name} {op}"
    if name:                                     # CallExpr, IdentifierExpr
        return f"{cls} {name}"
    return cls


def format_cfg(cfg: ControlFlowGraph) -> str:
    """Representación textual indentada del CFG (legible y procesable por IA)."""
    lines: List[str] = [f"CFG de '{cfg.function_name}'  ({len(cfg.blocks)} bloques)"]
    for block in cfg.blocks:
        marker = ""
        if block is cfg.entry:
            marker = "  [entry]"
        elif block is cfg.exit:
            marker = "  [exit]"
        lines.append(f"  {block.name}{marker}")
        if block.condition is not None:
            lines.append(f"      cond: {_stmt_summary(block.condition)}")
        for stmt in block.statements:
            lines.append(f"      · {_stmt_summary(stmt)}")
        if block.successors:
            for edge in block.successors:
                tag = f" [{edge.label}]" if edge.label else ""
                lines.append(f"      → {edge.target.name}{tag}")
        else:
            lines.append("      → (sin sucesores)")
    return "\n".join(lines)
