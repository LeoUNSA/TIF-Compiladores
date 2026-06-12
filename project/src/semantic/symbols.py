"""
Tabla de Símbolos para MiniLang.

Modela el registro de variables y funciones con su tipo, alcance (scope) y
posición de declaración en la fuente. Es una de las "fuentes de verdad" que el
Compilador Aumentado expone a la capa de IA para responder consultas como
`--describe <variable>` o `--navigate`.

Estructura:
  - `Symbol`  : una entrada (variable, parámetro o función).
  - `Scope`   : un ámbito léxico; diccionario nombre→Symbol con puntero al padre.
  - `SymbolTable` : pila de scopes anidados (global → función → bloque → ...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Symbol:
    """Entrada de la tabla de símbolos."""
    name:    str
    kind:    str                       # "var" | "param" | "func"
    type:    str                       # tipo del valor / tipo de retorno (func)
    line:    int = 0
    column:  int = 0
    # Solo para funciones:
    param_types: Optional[List[str]] = None   # tipos de los parámetros formales

    def __str__(self) -> str:
        if self.kind == "func":
            params = ", ".join(self.param_types or [])
            return f"func {self.type} {self.name}({params})"
        return f"{self.kind} {self.type} {self.name}"


class Scope:
    """Ámbito léxico: nombres declarados localmente + enlace al ámbito padre."""

    def __init__(self, parent: Optional["Scope"] = None, label: str = "") -> None:
        self.parent:  Optional["Scope"] = parent
        self.label:   str = label                 # "global", "func:factorial", "block"
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Declara `symbol` en ESTE ámbito.

        Devuelve False si ya existía un símbolo con el mismo nombre aquí
        (redeclaración en el mismo alcance); True si se insertó correctamente.
        """
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def resolve_local(self, name: str) -> Optional[Symbol]:
        """Busca `name` solo en este ámbito."""
        return self.symbols.get(name)

    def resolve(self, name: str) -> Optional[Symbol]:
        """Busca `name` en este ámbito y, si no está, en los ámbitos padres."""
        scope: Optional["Scope"] = self
        while scope is not None:
            found = scope.symbols.get(name)
            if found is not None:
                return found
            scope = scope.parent
        return None


class SymbolTable:
    """Pila de ámbitos. Empieza con un ámbito global y crece/decrece con bloques."""

    def __init__(self) -> None:
        self.global_scope = Scope(parent=None, label="global")
        self._stack: List[Scope] = [self.global_scope]

    @property
    def current(self) -> Scope:
        return self._stack[-1]

    def push_scope(self, label: str = "block") -> Scope:
        scope = Scope(parent=self.current, label=label)
        self._stack.append(scope)
        return scope

    def pop_scope(self) -> Scope:
        if len(self._stack) == 1:
            raise RuntimeError("No se puede salir del ámbito global")
        return self._stack.pop()

    # ── Atajos sobre el ámbito actual ─────────────────────────────────────

    def define(self, symbol: Symbol) -> bool:
        return self.current.define(symbol)

    def resolve(self, name: str) -> Optional[Symbol]:
        return self.current.resolve(name)

    def resolve_local(self, name: str) -> Optional[Symbol]:
        return self.current.resolve_local(name)
