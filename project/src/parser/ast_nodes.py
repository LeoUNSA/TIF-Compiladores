"""
Nodos del Árbol de Sintaxis Abstracta (AST) para MiniLang.

Cada nodo almacena la información necesaria para:
  - reconstruir la estructura del programa,
  - alimentar el análisis semántico y la generación de CFG,
  - ser consultado por la capa de IA para producir explicaciones accesibles.

Jerarquía:
  Node
  ├── Statement
  │   ├── Program
  │   ├── Block
  │   ├── FunctionDecl
  │   ├── VarDecl
  │   ├── IfStmt
  │   ├── WhileStmt
  │   ├── ForStmt
  │   ├── ReturnStmt
  │   ├── BreakStmt
  │   ├── ContinueStmt
  │   ├── PrintStmt
  │   ├── ReadStmt
  │   └── ExprStmt
  └── Expression
      ├── BinaryOp
      ├── UnaryOp
      ├── AssignExpr
      ├── CallExpr
      ├── IdentifierExpr
      ├── IntLiteral
      ├── FloatLiteral
      ├── StringLiteral
      ├── BoolLiteral
      └── NullLiteral
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Visitor pattern
# ─────────────────────────────────────────────────────────────────────────────

class Visitor(ABC):
    """Interfaz para el patrón Visitor sobre el AST."""

    # Statements
    @abstractmethod
    def visit_program(self, node: "Program") -> object: ...
    @abstractmethod
    def visit_block(self, node: "Block") -> object: ...
    @abstractmethod
    def visit_function_decl(self, node: "FunctionDecl") -> object: ...
    @abstractmethod
    def visit_var_decl(self, node: "VarDecl") -> object: ...
    @abstractmethod
    def visit_if_stmt(self, node: "IfStmt") -> object: ...
    @abstractmethod
    def visit_while_stmt(self, node: "WhileStmt") -> object: ...
    @abstractmethod
    def visit_for_stmt(self, node: "ForStmt") -> object: ...
    @abstractmethod
    def visit_return_stmt(self, node: "ReturnStmt") -> object: ...
    @abstractmethod
    def visit_break_stmt(self, node: "BreakStmt") -> object: ...
    @abstractmethod
    def visit_continue_stmt(self, node: "ContinueStmt") -> object: ...
    @abstractmethod
    def visit_print_stmt(self, node: "PrintStmt") -> object: ...
    @abstractmethod
    def visit_read_stmt(self, node: "ReadStmt") -> object: ...
    @abstractmethod
    def visit_expr_stmt(self, node: "ExprStmt") -> object: ...

    # Expressions
    @abstractmethod
    def visit_binary_op(self, node: "BinaryOp") -> object: ...
    @abstractmethod
    def visit_unary_op(self, node: "UnaryOp") -> object: ...
    @abstractmethod
    def visit_assign_expr(self, node: "AssignExpr") -> object: ...
    @abstractmethod
    def visit_call_expr(self, node: "CallExpr") -> object: ...
    @abstractmethod
    def visit_identifier(self, node: "IdentifierExpr") -> object: ...
    @abstractmethod
    def visit_int_literal(self, node: "IntLiteral") -> object: ...
    @abstractmethod
    def visit_float_literal(self, node: "FloatLiteral") -> object: ...
    @abstractmethod
    def visit_string_literal(self, node: "StringLiteral") -> object: ...
    @abstractmethod
    def visit_bool_literal(self, node: "BoolLiteral") -> object: ...
    @abstractmethod
    def visit_null_literal(self, node: "NullLiteral") -> object: ...


# ─────────────────────────────────────────────────────────────────────────────
# Nodo base
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Node(ABC):
    """Nodo base del AST. Almacena posición en la fuente.

    `line` y `column` son keyword-only (kw_only=True) para evitar
    conflictos de ordering con los campos sin default de las subclases.
    """
    line:   int = field(default=0, compare=False, repr=False, kw_only=True)
    column: int = field(default=0, compare=False, repr=False, kw_only=True)

    @abstractmethod
    def accept(self, visitor: Visitor) -> object: ...


# ─────────────────────────────────────────────────────────────────────────────
# Declaraciones / Sentencias
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Statement(Node, ABC):
    """Nodo base para sentencias."""


@dataclass
class Program(Statement):
    """Nodo raíz: lista de declaraciones en el nivel superior."""
    body: List[Statement] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_program(self)


@dataclass
class Block(Statement):
    """Bloque de sentencias entre { }."""
    body: List[Statement] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_block(self)


@dataclass
class Param:
    """Parámetro formal de una función: (tipo, nombre)."""
    type_name: str
    name:      str
    line:      int = field(default=0, compare=False, repr=False)
    column:    int = field(default=0, compare=False, repr=False)


@dataclass
class FunctionDecl(Statement):
    """Declaración de función: func <tipo> <nombre>(<params>) <bloque>."""
    name:        str
    return_type: str
    params:      List[Param]
    body:        Block

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_function_decl(self)


@dataclass
class VarDecl(Statement):
    """Declaración de variable: <tipo> <nombre> [= <expr>] ;"""
    type_name:   str
    name:        str
    initializer: Optional["Expression"] = None

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_var_decl(self)


@dataclass
class IfStmt(Statement):
    """if (<cond>) <then> [else <else_>]"""
    condition: "Expression"
    then_branch: Block
    else_branch: Optional[Statement] = None  # Block o IfStmt anidado

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_if_stmt(self)


@dataclass
class WhileStmt(Statement):
    """while (<cond>) <bloque>"""
    condition: "Expression"
    body:      Block

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_while_stmt(self)


@dataclass
class ForStmt(Statement):
    """for (<init>; <cond>; <update>) <bloque>"""
    init:      Optional[Statement]     # VarDecl o ExprStmt o None
    condition: Optional["Expression"]
    update:    Optional["Expression"]
    body:      Block

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_for_stmt(self)


@dataclass
class ReturnStmt(Statement):
    """return [<expr>] ;"""
    value: Optional["Expression"] = None

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_return_stmt(self)


@dataclass
class BreakStmt(Statement):
    """break ;"""
    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_break_stmt(self)


@dataclass
class ContinueStmt(Statement):
    """continue ;"""
    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_continue_stmt(self)


@dataclass
class PrintStmt(Statement):
    """print(<expr>, ...) ;"""
    args: List["Expression"] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_print_stmt(self)


@dataclass
class ReadStmt(Statement):
    """read(<ident>, ...) ;"""
    targets: List[str] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_read_stmt(self)


@dataclass
class ExprStmt(Statement):
    """Sentencia expresión: <expr> ;"""
    expr: "Expression"

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_expr_stmt(self)


# ─────────────────────────────────────────────────────────────────────────────
# Expresiones
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Expression(Node, ABC):
    """Nodo base para expresiones."""


@dataclass
class BinaryOp(Expression):
    """Operación binaria: <left> <op> <right>"""
    left:     Expression
    operator: str          # lexema del operador: "+", "==", "&&", etc.
    right:    Expression

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_binary_op(self)


@dataclass
class UnaryOp(Expression):
    """Operación unaria: <op> <operand>"""
    operator: str          # "-" | "!"
    operand:  Expression

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_unary_op(self)


@dataclass
class AssignExpr(Expression):
    """Asignación: <nombre> <op> <value>"""
    name:     str
    operator: str          # "=" | "+=" | "-=" | "*=" | "/="
    value:    Expression

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_assign_expr(self)


@dataclass
class CallExpr(Expression):
    """Llamada a función: <nombre>(<args>)"""
    name:      str
    arguments: List[Expression] = field(default_factory=list)

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_call_expr(self)


@dataclass
class IdentifierExpr(Expression):
    """Referencia a una variable: <nombre>"""
    name: str

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_identifier(self)


@dataclass
class IntLiteral(Expression):
    """Literal entero."""
    value: int

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_int_literal(self)


@dataclass
class FloatLiteral(Expression):
    """Literal flotante."""
    value: float

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_float_literal(self)


@dataclass
class StringLiteral(Expression):
    """Literal de cadena."""
    value: str

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_string_literal(self)


@dataclass
class BoolLiteral(Expression):
    """Literal booleano: true | false"""
    value: bool

    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_bool_literal(self)


@dataclass
class NullLiteral(Expression):
    """Literal nulo: null"""
    def accept(self, visitor: Visitor) -> object:
        return visitor.visit_null_literal(self)
