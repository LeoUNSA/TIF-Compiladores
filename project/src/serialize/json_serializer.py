"""
Serializador del AST a estructuras JSON-compatibles.

`JsonSerializer` es el quinto `Visitor` del AST (tras ASTPrinter, SemanticAnalyzer
y CFGBuilder). Convierte cualquier nodo en un diccionario anidado de tipos
primitivos (dict/list/str/int/float/bool/None), listo para `json.dumps`.

Cada nodo expresión incluye su `type` = `inferred_type` calculado por el análisis
semántico, de modo que el JSON resultante es contexto verificado para la capa de IA
(no texto fuente ambiguo). Es la base de las consultas `--explain-function`,
`--describe`, `--explain-error` y `--navigate` descritas en la propuesta.
"""

from __future__ import annotations

from typing import List, Optional

from ..parser.ast_nodes import (
    AssignExpr, BinaryOp, Block, BoolLiteral, BreakStmt, CallExpr,
    ContinueStmt, ExprStmt, FloatLiteral, ForStmt, FunctionDecl,
    IdentifierExpr, IfStmt, IntLiteral, NullLiteral, PrintStmt, Program,
    ReadStmt, ReturnStmt, StringLiteral, UnaryOp, VarDecl, Visitor,
    WhileStmt,
)


class JsonSerializer(Visitor):
    """Convierte un nodo AST en un diccionario JSON-compatible."""

    # ── API pública ───────────────────────────────────────────────────────

    def serialize(self, node) -> object:
        """Serializa un nodo (o None) a estructura JSON-compatible."""
        if node is None:
            return None
        return node.accept(self)

    def _list(self, nodes: List) -> list:
        return [self.serialize(n) for n in nodes]

    @staticmethod
    def _pos(node) -> dict:
        return {"line": getattr(node, "line", 0), "column": getattr(node, "column", 0)}

    # ── Statements ────────────────────────────────────────────────────────

    def visit_program(self, node: Program) -> object:
        return {"node": "Program", "body": self._list(node.body)}

    def visit_block(self, node: Block) -> object:
        return {"node": "Block", **self._pos(node), "body": self._list(node.body)}

    def visit_function_decl(self, node: FunctionDecl) -> object:
        return {
            "node": "FunctionDecl", **self._pos(node),
            "name": node.name, "return_type": node.return_type,
            "params": [
                {"name": p.name, "type": p.type_name,
                 "line": p.line, "column": p.column}
                for p in node.params
            ],
            "body": self.serialize(node.body),
        }

    def visit_var_decl(self, node: VarDecl) -> object:
        return {
            "node": "VarDecl", **self._pos(node),
            "type": node.type_name, "name": node.name,
            "initializer": self.serialize(node.initializer),
        }

    def visit_if_stmt(self, node: IfStmt) -> object:
        return {
            "node": "IfStmt", **self._pos(node),
            "condition": self.serialize(node.condition),
            "then": self.serialize(node.then_branch),
            "else": self.serialize(node.else_branch),
        }

    def visit_while_stmt(self, node: WhileStmt) -> object:
        return {
            "node": "WhileStmt", **self._pos(node),
            "condition": self.serialize(node.condition),
            "body": self.serialize(node.body),
        }

    def visit_for_stmt(self, node: ForStmt) -> object:
        return {
            "node": "ForStmt", **self._pos(node),
            "init": self.serialize(node.init),
            "condition": self.serialize(node.condition),
            "update": self.serialize(node.update),
            "body": self.serialize(node.body),
        }

    def visit_return_stmt(self, node: ReturnStmt) -> object:
        return {"node": "ReturnStmt", **self._pos(node),
                "value": self.serialize(node.value)}

    def visit_break_stmt(self, node: BreakStmt) -> object:
        return {"node": "BreakStmt", **self._pos(node)}

    def visit_continue_stmt(self, node: ContinueStmt) -> object:
        return {"node": "ContinueStmt", **self._pos(node)}

    def visit_print_stmt(self, node: PrintStmt) -> object:
        return {"node": "PrintStmt", **self._pos(node), "args": self._list(node.args)}

    def visit_read_stmt(self, node: ReadStmt) -> object:
        return {"node": "ReadStmt", **self._pos(node), "targets": list(node.targets)}

    def visit_expr_stmt(self, node: ExprStmt) -> object:
        return {"node": "ExprStmt", **self._pos(node), "expr": self.serialize(node.expr)}

    # ── Expressions (incluyen el tipo inferido) ───────────────────────────

    def _expr(self, node, **extra) -> dict:
        return {"node": type(node).__name__, "type": node.inferred_type,
                **self._pos(node), **extra}

    def visit_binary_op(self, node: BinaryOp) -> object:
        return self._expr(node, operator=node.operator,
                          left=self.serialize(node.left),
                          right=self.serialize(node.right))

    def visit_unary_op(self, node: UnaryOp) -> object:
        return self._expr(node, operator=node.operator,
                          operand=self.serialize(node.operand))

    def visit_assign_expr(self, node: AssignExpr) -> object:
        return self._expr(node, name=node.name, operator=node.operator,
                          value=self.serialize(node.value))

    def visit_call_expr(self, node: CallExpr) -> object:
        return self._expr(node, name=node.name,
                          arguments=self._list(node.arguments))

    def visit_identifier(self, node: IdentifierExpr) -> object:
        return self._expr(node, name=node.name)

    def visit_int_literal(self, node: IntLiteral) -> object:
        return self._expr(node, value=node.value)

    def visit_float_literal(self, node: FloatLiteral) -> object:
        return self._expr(node, value=node.value)

    def visit_string_literal(self, node: StringLiteral) -> object:
        return self._expr(node, value=node.value)

    def visit_bool_literal(self, node: BoolLiteral) -> object:
        return self._expr(node, value=node.value)

    def visit_null_literal(self, node: NullLiteral) -> object:
        return self._expr(node, value=None)
