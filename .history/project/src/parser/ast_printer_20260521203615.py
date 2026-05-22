"""
AST Printer — imprime el árbol de sintaxis abstracta de MiniLang
en formato indentado, apto para ser leído por personas o procesado
por la capa de IA del Compilador Aumentado.
"""

from __future__ import annotations

import io
from .ast_nodes import (
    AssignExpr, BinaryOp, Block, BoolLiteral, BreakStmt, CallExpr,
    ContinueStmt, ExprStmt, FloatLiteral, ForStmt, FunctionDecl,
    IdentifierExpr, IfStmt, IntLiteral, NullLiteral, PrintStmt, Program,
    ReadStmt, ReturnStmt, StringLiteral, UnaryOp, VarDecl, Visitor,
    WhileStmt,
)


class ASTPrinter(Visitor):
    """Genera una representación legible del AST de MiniLang."""

    def __init__(self, indent: int = 2) -> None:
        self._indent  = indent
        self._depth   = 0
        self._buf     = io.StringIO()

    # ── API pública ───────────────────────────────────────────────────────

    def print(self, node) -> str:
        self._buf   = io.StringIO()
        self._depth = 0
        node.accept(self)
        return self._buf.getvalue()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _write(self, text: str) -> None:
        pad = " " * (self._depth * self._indent)
        self._buf.write(pad + text + "\n")

    def _branch(self, label: str, children) -> None:
        self._write(label)
        self._depth += 1
        for child in children:
            if child is not None:
                child.accept(self)
        self._depth -= 1

    # ── Sentencias ────────────────────────────────────────────────────────

    def visit_program(self, node: Program) -> None:
        self._branch("Program", node.body)

    def visit_block(self, node: Block) -> None:
        self._branch("Block", node.body)

    def visit_function_decl(self, node: FunctionDecl) -> None:
        params_str = ", ".join(
            f"{p.type_name} {p.name}" for p in node.params
        )
        self._write(
            f"FunctionDecl  name={node.name}  "
            f"return={node.return_type}  params=({params_str})"
        )
        self._depth += 1
        node.body.accept(self)
        self._depth -= 1

    def visit_var_decl(self, node: VarDecl) -> None:
        has_init = node.initializer is not None
        self._write(
            f"VarDecl  type={node.type_name}  name={node.name}"
            + ("  =" if has_init else "")
        )
        if has_init:
            self._depth += 1
            node.initializer.accept(self)
            self._depth -= 1

    def visit_if_stmt(self, node: IfStmt) -> None:
        self._write("IfStmt")
        self._depth += 1
        self._write("condition:")
        self._depth += 1
        node.condition.accept(self)
        self._depth -= 1
        self._write("then:")
        self._depth += 1
        node.then_branch.accept(self)
        self._depth -= 1
        if node.else_branch is not None:
            self._write("else:")
            self._depth += 1
            node.else_branch.accept(self)
            self._depth -= 1
        self._depth -= 1

    def visit_while_stmt(self, node: WhileStmt) -> None:
        self._write("WhileStmt")
        self._depth += 1
        self._write("condition:")
        self._depth += 1
        node.condition.accept(self)
        self._depth -= 1
        self._write("body:")
        self._depth += 1
        node.body.accept(self)
        self._depth -= 1
        self._depth -= 1

    def visit_for_stmt(self, node: ForStmt) -> None:
        self._write("ForStmt")
        self._depth += 1
        self._write("init:")
        self._depth += 1
        if node.init:
            node.init.accept(self)
        else:
            self._write("(vacío)")
        self._depth -= 1
        self._write("condition:")
        self._depth += 1
        if node.condition:
            node.condition.accept(self)
        else:
            self._write("(vacío — siempre true)")
        self._depth -= 1
        self._write("update:")
        self._depth += 1
        if node.update:
            node.update.accept(self)
        else:
            self._write("(vacío)")
        self._depth -= 1
        self._write("body:")
        self._depth += 1
        node.body.accept(self)
        self._depth -= 1
        self._depth -= 1

    def visit_return_stmt(self, node: ReturnStmt) -> None:
        self._write("ReturnStmt")
        if node.value:
            self._depth += 1
            node.value.accept(self)
            self._depth -= 1

    def visit_break_stmt(self, node: BreakStmt) -> None:
        self._write("BreakStmt")

    def visit_continue_stmt(self, node: ContinueStmt) -> None:
        self._write("ContinueStmt")

    def visit_print_stmt(self, node: PrintStmt) -> None:
        self._write(f"PrintStmt  ({len(node.args)} arg(s))")
        self._depth += 1
        for arg in node.args:
            arg.accept(self)
        self._depth -= 1

    def visit_read_stmt(self, node: ReadStmt) -> None:
        self._write(f"ReadStmt  targets=[{', '.join(node.targets)}]")

    def visit_expr_stmt(self, node: ExprStmt) -> None:
        self._write("ExprStmt")
        self._depth += 1
        node.expr.accept(self)
        self._depth -= 1

    # ── Expresiones ───────────────────────────────────────────────────────

    def visit_binary_op(self, node: BinaryOp) -> None:
        self._write(f"BinaryOp  op={node.operator!r}")
        self._depth += 1
        node.left.accept(self)
        node.right.accept(self)
        self._depth -= 1

    def visit_unary_op(self, node: UnaryOp) -> None:
        self._write(f"UnaryOp  op={node.operator!r}")
        self._depth += 1
        node.operand.accept(self)
        self._depth -= 1

    def visit_assign_expr(self, node: AssignExpr) -> None:
        self._write(f"AssignExpr  name={node.name}  op={node.operator!r}")
        self._depth += 1
        node.value.accept(self)
        self._depth -= 1

    def visit_call_expr(self, node: CallExpr) -> None:
        self._write(f"CallExpr  name={node.name}  args={len(node.arguments)}")
        self._depth += 1
        for arg in node.arguments:
            arg.accept(self)
        self._depth -= 1

    def visit_identifier(self, node: IdentifierExpr) -> None:
        self._write(f"Identifier  name={node.name}")

    def visit_int_literal(self, node: IntLiteral) -> None:
        self._write(f"IntLiteral  {node.value}")

    def visit_float_literal(self, node: FloatLiteral) -> None:
        self._write(f"FloatLiteral  {node.value}")

    def visit_string_literal(self, node: StringLiteral) -> None:
        self._write(f"StringLiteral  {node.value!r}")

    def visit_bool_literal(self, node: BoolLiteral) -> None:
        self._write(f"BoolLiteral  {node.value}")

    def visit_null_literal(self, node: NullLiteral) -> None:
        self._write("NullLiteral")
