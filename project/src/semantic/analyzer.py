"""
Analizador Semántico de MiniLang.

Recorre el AST (patrón Visitor) y realiza:
  - construcción de la tabla de símbolos con ámbitos anidados,
  - verificación estática de tipos (estricta, sin coerción int↔float),
  - detección de variables/funciones no declaradas y redeclaraciones,
  - verificación de aridad y tipos en llamadas a funciones,
  - comprobación de que `break`/`continue` aparezcan solo dentro de bucles,
  - comprobación de que las condiciones de `if`/`while`/`for` sean `bool`,
  - verificación de tipos de retorno.

Decora cada nodo Expression con `inferred_type` y recolecta TODOS los errores
(no aborta en el primero) para producir un diagnóstico pedagógicamente completo.
Si una expresión es errónea, su tipo inferido es `None` (tipo "veneno") y no
genera errores en cascada.
"""

from __future__ import annotations

from typing import List, Optional

from ..errors import SemanticError
from ..parser.ast_nodes import (
    AssignExpr, BinaryOp, Block, BoolLiteral, BreakStmt, CallExpr,
    ContinueStmt, ExprStmt, FloatLiteral, ForStmt, FunctionDecl,
    IdentifierExpr, IfStmt, IntLiteral, NullLiteral, PrintStmt, Program,
    ReadStmt, ReturnStmt, StringLiteral, UnaryOp, VarDecl, Visitor,
    WhileStmt,
)
from .symbols import Symbol, SymbolTable

NUMERIC = {"int", "float"}
ARITH_OPS = {"+", "-", "*", "/", "%"}
COMPARE_OPS = {"<", "<=", ">", ">="}
EQUALITY_OPS = {"==", "!="}
LOGIC_OPS = {"&&", "||"}


class SemanticAnalyzer(Visitor):
    """Verifica la semántica de un Programa y construye su tabla de símbolos."""

    def __init__(self) -> None:
        self.table = SymbolTable()
        self.errors: List[SemanticError] = []
        # Pilas de contexto para validaciones dependientes del entorno:
        self._return_types: List[str] = []   # tipo de retorno de la función actual
        self._loop_depth: int = 0             # >0 ⇒ dentro de un bucle

    # ── API pública ───────────────────────────────────────────────────────

    def analyze(self, program: Program) -> List[SemanticError]:
        """Analiza `program`; devuelve la lista de errores (vacía si todo OK)."""
        program.accept(self)
        return self.errors

    # ── Helpers ───────────────────────────────────────────────────────────

    def _error(self, message: str, node) -> None:
        line = getattr(node, "line", 0)
        column = getattr(node, "column", 0)
        self.errors.append(SemanticError(message, line, column))

    def _eval(self, expr) -> Optional[str]:
        """Visita una expresión y devuelve su tipo inferido (None si erróneo)."""
        t = expr.accept(self)
        expr.inferred_type = t
        return t

    # ── Statements ────────────────────────────────────────────────────────

    def visit_program(self, node: Program) -> object:
        # Pre-pase: registra todas las firmas de función para permitir
        # llamadas hacia adelante (una función puede llamar a otra declarada
        # más abajo, y la recursión funciona).
        for stmt in node.body:
            if isinstance(stmt, FunctionDecl):
                self._declare_function(stmt)
        for stmt in node.body:
            stmt.accept(self)
        return None

    def _declare_function(self, node: FunctionDecl) -> None:
        param_types = [p.type_name for p in node.params]
        sym = Symbol(
            name=node.name, kind="func", type=node.return_type,
            line=node.line, column=node.column, param_types=param_types,
        )
        if not self.table.define(sym):
            self._error(f"Función '{node.name}' ya declarada en este ámbito", node)

    def visit_function_decl(self, node: FunctionDecl) -> object:
        # La firma ya se registró en el pre-pase; aquí analizamos el cuerpo.
        self.table.push_scope(label=f"func:{node.name}")
        for p in node.params:
            sym = Symbol(name=p.name, kind="param", type=p.type_name,
                         line=p.line, column=p.column)
            if not self.table.define(sym):
                self._error(f"Parámetro '{p.name}' duplicado en '{node.name}'", node)
        self._return_types.append(node.return_type)
        # El cuerpo es un Block; lo recorremos en el mismo ámbito de la función
        # (no abrimos un scope extra) para que los parámetros sean visibles.
        for stmt in node.body.body:
            stmt.accept(self)
        self._return_types.pop()
        self.table.pop_scope()
        return None

    def visit_block(self, node: Block) -> object:
        self.table.push_scope(label="block")
        for stmt in node.body:
            stmt.accept(self)
        self.table.pop_scope()
        return None

    def visit_var_decl(self, node: VarDecl) -> object:
        if node.type_name == "void":
            self._error(f"No se puede declarar la variable '{node.name}' de tipo void", node)
        if self.table.resolve_local(node.name) is not None:
            self._error(f"Variable '{node.name}' ya declarada en este ámbito", node)
        else:
            self.table.define(Symbol(name=node.name, kind="var", type=node.type_name,
                                     line=node.line, column=node.column))
        if node.initializer is not None:
            init_type = self._eval(node.initializer)
            if init_type is not None and init_type != node.type_name:
                self._error(
                    f"No se puede asignar un valor '{init_type}' a la variable "
                    f"'{node.name}' de tipo '{node.type_name}'",
                    node,
                )
        return None

    def visit_if_stmt(self, node: IfStmt) -> object:
        self._check_condition(node.condition, "if")
        node.then_branch.accept(self)
        if node.else_branch is not None:
            node.else_branch.accept(self)
        return None

    def visit_while_stmt(self, node: WhileStmt) -> object:
        self._check_condition(node.condition, "while")
        self._loop_depth += 1
        node.body.accept(self)
        self._loop_depth -= 1
        return None

    def visit_for_stmt(self, node: ForStmt) -> object:
        # El init puede declarar una variable visible solo dentro del for.
        self.table.push_scope(label="for")
        if node.init is not None:
            node.init.accept(self)
        if node.condition is not None:
            self._check_condition(node.condition, "for")
        if node.update is not None:
            self._eval(node.update)
        self._loop_depth += 1
        node.body.accept(self)
        self._loop_depth -= 1
        self.table.pop_scope()
        return None

    def visit_return_stmt(self, node: ReturnStmt) -> object:
        if not self._return_types:
            self._error("'return' fuera de una función", node)
            if node.value is not None:
                self._eval(node.value)
            return None
        expected = self._return_types[-1]
        if node.value is None:
            if expected != "void":
                self._error(f"La función debe retornar un valor de tipo '{expected}'", node)
        else:
            actual = self._eval(node.value)
            if expected == "void":
                self._error("Una función void no puede retornar un valor", node)
            elif actual is not None and actual != expected:
                self._error(
                    f"Tipo de retorno '{actual}' incompatible con '{expected}'", node)
        return None

    def visit_break_stmt(self, node: BreakStmt) -> object:
        if self._loop_depth == 0:
            self._error("'break' solo puede usarse dentro de un bucle", node)
        return None

    def visit_continue_stmt(self, node: ContinueStmt) -> object:
        if self._loop_depth == 0:
            self._error("'continue' solo puede usarse dentro de un bucle", node)
        return None

    def visit_print_stmt(self, node: PrintStmt) -> object:
        for arg in node.args:
            self._eval(arg)   # print acepta cualquier tipo
        return None

    def visit_read_stmt(self, node: ReadStmt) -> object:
        for name in node.targets:
            if self.table.resolve(name) is None:
                self._error(f"Variable no declarada: '{name}'", node)
        return None

    def visit_expr_stmt(self, node: ExprStmt) -> object:
        self._eval(node.expr)
        return None

    # ── Expressions (devuelven el tipo inferido o None) ───────────────────

    def visit_binary_op(self, node: BinaryOp) -> object:
        left = self._eval(node.left)
        right = self._eval(node.right)
        if left is None or right is None:
            return None
        op = node.operator
        if op in ARITH_OPS:
            if op == "%" and not (left == "int" and right == "int"):
                self._error("El operador '%' requiere operandos 'int'", node)
                return None
            if left in NUMERIC and right in NUMERIC and left == right:
                return left
            self._error(
                f"Operador '{op}' no aplicable a '{left}' y '{right}'", node)
            return None
        if op in COMPARE_OPS:
            if left in NUMERIC and right in NUMERIC and left == right:
                return "bool"
            self._error(
                f"Operador '{op}' requiere operandos numéricos del mismo tipo, "
                f"recibió '{left}' y '{right}'", node)
            return None
        if op in EQUALITY_OPS:
            if left == right:
                return "bool"
            self._error(
                f"No se pueden comparar tipos distintos: '{left}' y '{right}'", node)
            return None
        if op in LOGIC_OPS:
            if left == "bool" and right == "bool":
                return "bool"
            self._error(
                f"Operador '{op}' requiere operandos 'bool', "
                f"recibió '{left}' y '{right}'", node)
            return None
        self._error(f"Operador binario desconocido: '{op}'", node)
        return None

    def visit_unary_op(self, node: UnaryOp) -> object:
        t = self._eval(node.operand)
        if t is None:
            return None
        if node.operator == "-":
            if t in NUMERIC:
                return t
            self._error(f"Operador unario '-' no aplicable a '{t}'", node)
            return None
        if node.operator == "!":
            if t == "bool":
                return "bool"
            self._error(f"Operador unario '!' requiere 'bool', recibió '{t}'", node)
            return None
        self._error(f"Operador unario desconocido: '{node.operator}'", node)
        return None

    def visit_assign_expr(self, node: AssignExpr) -> object:
        sym = self.table.resolve(node.name)
        value_type = self._eval(node.value)
        if sym is None:
            self._error(f"Variable no declarada: '{node.name}'", node)
            return None
        if sym.kind == "func":
            self._error(f"No se puede asignar a la función '{node.name}'", node)
            return None
        if node.operator != "=":   # compuestos: += -= *= /= ⇒ numéricos
            if sym.type not in NUMERIC:
                self._error(
                    f"Operador '{node.operator}' requiere variable numérica, "
                    f"'{node.name}' es '{sym.type}'", node)
                return None
        if value_type is not None and value_type != sym.type:
            self._error(
                f"No se puede asignar '{value_type}' a '{node.name}' "
                f"de tipo '{sym.type}'", node)
            return None
        return sym.type

    def visit_call_expr(self, node: CallExpr) -> object:
        sym = self.table.resolve(node.name)
        arg_types = [self._eval(a) for a in node.arguments]
        if sym is None:
            self._error(f"Función no declarada: '{node.name}'", node)
            return None
        if sym.kind != "func":
            self._error(f"'{node.name}' no es una función", node)
            return None
        expected = sym.param_types or []
        if len(arg_types) != len(expected):
            self._error(
                f"La función '{node.name}' espera {len(expected)} argumento(s), "
                f"recibió {len(arg_types)}", node)
            return sym.type
        for i, (got, want) in enumerate(zip(arg_types, expected)):
            if got is not None and got != want:
                self._error(
                    f"Argumento {i + 1} de '{node.name}': se esperaba '{want}', "
                    f"se recibió '{got}'", node)
        return sym.type

    def visit_identifier(self, node: IdentifierExpr) -> object:
        sym = self.table.resolve(node.name)
        if sym is None:
            self._error(f"Variable no declarada: '{node.name}'", node)
            return None
        if sym.kind == "func":
            self._error(f"'{node.name}' es una función, no una variable", node)
            return None
        return sym.type

    def visit_int_literal(self, node: IntLiteral) -> object:
        return "int"

    def visit_float_literal(self, node: FloatLiteral) -> object:
        return "float"

    def visit_string_literal(self, node: StringLiteral) -> object:
        return "string"

    def visit_bool_literal(self, node: BoolLiteral) -> object:
        return "bool"

    def visit_null_literal(self, node: NullLiteral) -> object:
        return "null"

    # ── Helper de condición ───────────────────────────────────────────────

    def _check_condition(self, cond, ctx: str) -> None:
        t = self._eval(cond)
        if t is not None and t != "bool":
            self._error(
                f"La condición de '{ctx}' debe ser 'bool', recibió '{t}'", cond)
