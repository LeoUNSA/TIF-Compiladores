"""
Constructor del Grafo de Flujo de Control (CFG) de MiniLang.

`CFGBuilder` es el cuarto `Visitor` del AST (tras ASTPrinter y SemanticAnalyzer).
Construye un `ControlFlowGraph` por cada función del programa.

Modelo de construcción
-----------------------
El recorrido hila un "bloque actual" (`self._current`) que se va rellenando con
sentencias de flujo lineal. Cada `visit_*` de sentencia:
  - añade nodos al bloque actual, y/o
  - crea bloques nuevos y aristas para el flujo condicional/de bucle, y
  - deja en `self._current` el bloque por donde continúa la ejecución, o `None`
    si la ejecución terminó en esa rama (return / break / continue ⇒ código
    inalcanzable a continuación).

Las expresiones se tratan de forma atómica (no se modela el cortocircuito de
`&&`/`||` como ramas): se registran como parte del bloque que las contiene. Esto
basta para explicar el flujo a nivel de sentencia, que es el objetivo del paper.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..parser.ast_nodes import (
    AssignExpr, BinaryOp, Block, BoolLiteral, BreakStmt, CallExpr,
    ContinueStmt, ExprStmt, FloatLiteral, ForStmt, FunctionDecl,
    IdentifierExpr, IfStmt, IntLiteral, NullLiteral, PrintStmt, Program,
    ReadStmt, ReturnStmt, StringLiteral, UnaryOp, VarDecl, Visitor,
    WhileStmt,
)
from .blocks import BasicBlock, ControlFlowGraph


class CFGBuilder(Visitor):
    """Construye un CFG por función a partir del AST."""

    def __init__(self) -> None:
        self.cfg: Optional[ControlFlowGraph] = None
        self._current: Optional[BasicBlock] = None
        # Pila de bucles activos: (destino de 'continue', destino de 'break').
        self._loops: List[Tuple[BasicBlock, BasicBlock]] = []

    # ── API pública ───────────────────────────────────────────────────────

    def build(self, program: Program) -> List[ControlFlowGraph]:
        """Devuelve un CFG por cada FunctionDecl de nivel superior."""
        cfgs: List[ControlFlowGraph] = []
        for stmt in program.body:
            if isinstance(stmt, FunctionDecl):
                cfgs.append(self._build_function(stmt))
        return cfgs

    def _build_function(self, fn: FunctionDecl) -> ControlFlowGraph:
        cfg = ControlFlowGraph(fn.name)
        self.cfg = cfg
        self._loops = []
        cfg.entry = cfg.new_block("entry")
        cfg.exit  = cfg.new_block("exit")
        self._current = cfg.entry
        for stmt in fn.body.body:
            stmt.accept(self)
        # Caída implícita al final del cuerpo ⇒ arista al bloque de salida.
        if self._current is not None:
            ControlFlowGraph.connect(self._current, cfg.exit)
        return cfg

    # ── Helpers ───────────────────────────────────────────────────────────

    def _emit(self, node) -> None:
        """Añade una sentencia de flujo lineal al bloque actual (si es alcanzable)."""
        if self._current is not None:
            self._current.statements.append(node)

    def _new(self, label: str) -> BasicBlock:
        assert self.cfg is not None
        return self.cfg.new_block(label)

    # ── Sentencias de flujo lineal ────────────────────────────────────────

    def visit_var_decl(self, node: VarDecl) -> object:
        self._emit(node); return None

    def visit_expr_stmt(self, node: ExprStmt) -> object:
        self._emit(node); return None

    def visit_print_stmt(self, node: PrintStmt) -> object:
        self._emit(node); return None

    def visit_read_stmt(self, node: ReadStmt) -> object:
        self._emit(node); return None

    def visit_block(self, node: Block) -> object:
        # Un bloque léxico { } no abre un bloque básico nuevo: solo secuencia.
        for stmt in node.body:
            stmt.accept(self)
        return None

    # ── Saltos: terminan el bloque actual ─────────────────────────────────

    def visit_return_stmt(self, node: ReturnStmt) -> object:
        if self._current is None:
            return None
        self._emit(node)
        ControlFlowGraph.connect(self._current, self.cfg.exit)
        self._current = None
        return None

    def visit_break_stmt(self, node: BreakStmt) -> object:
        if self._current is None or not self._loops:
            return None
        self._emit(node)
        _, brk = self._loops[-1]
        ControlFlowGraph.connect(self._current, brk, "break")
        self._current = None
        return None

    def visit_continue_stmt(self, node: ContinueStmt) -> object:
        if self._current is None or not self._loops:
            return None
        self._emit(node)
        cont, _ = self._loops[-1]
        ControlFlowGraph.connect(self._current, cont, "continue")
        self._current = None
        return None

    # ── Flujo condicional / bucles ────────────────────────────────────────

    def visit_if_stmt(self, node: IfStmt) -> object:
        if self._current is None:
            return None
        cond_block = self._current
        cond_block.condition = node.condition

        then_block = self._new("if.then")
        ControlFlowGraph.connect(cond_block, then_block, "true")
        self._current = then_block
        node.then_branch.accept(self)
        then_end = self._current

        if node.else_branch is not None:
            else_block = self._new("if.else")
            ControlFlowGraph.connect(cond_block, else_block, "false")
            self._current = else_block
            node.else_branch.accept(self)
            else_end = self._current
            cont = [b for b in (then_end, else_end) if b is not None]
            if cont:
                merge = self._new("if.end")
                for b in cont:
                    ControlFlowGraph.connect(b, merge)
                self._current = merge
            else:
                self._current = None          # ambas ramas terminan (return)
        else:
            merge = self._new("if.end")
            ControlFlowGraph.connect(cond_block, merge, "false")
            if then_end is not None:
                ControlFlowGraph.connect(then_end, merge)
            self._current = merge
        return None

    def visit_while_stmt(self, node: WhileStmt) -> object:
        if self._current is None:
            return None
        header = self._new("while.cond")
        header.condition = node.condition
        ControlFlowGraph.connect(self._current, header)

        body_block = self._new("while.body")
        exit_block = self._new("while.end")
        ControlFlowGraph.connect(header, body_block, "true")
        ControlFlowGraph.connect(header, exit_block, "false")

        self._loops.append((header, exit_block))   # continue→header, break→exit
        self._current = body_block
        node.body.accept(self)
        if self._current is not None:
            ControlFlowGraph.connect(self._current, header)   # arista de retroceso
        self._loops.pop()
        self._current = exit_block
        return None

    def visit_for_stmt(self, node: ForStmt) -> object:
        if self._current is None:
            return None
        if node.init is not None:
            node.init.accept(self)             # init va en el bloque actual

        header = self._new("for.cond")
        if node.condition is not None:
            header.condition = node.condition
        ControlFlowGraph.connect(self._current, header)

        body_block   = self._new("for.body")
        update_block = self._new("for.update")
        exit_block   = self._new("for.end")

        ControlFlowGraph.connect(header, body_block, "true")
        if node.condition is not None:
            ControlFlowGraph.connect(header, exit_block, "false")

        # En un for, 'continue' salta al update (para que se ejecute), 'break' al exit.
        self._loops.append((update_block, exit_block))
        self._current = body_block
        node.body.accept(self)
        if self._current is not None:
            ControlFlowGraph.connect(self._current, update_block)

        if node.update is not None:
            update_block.statements.append(node.update)
        ControlFlowGraph.connect(update_block, header)   # vuelve a evaluar la condición

        self._loops.pop()
        self._current = exit_block
        return None

    def visit_function_decl(self, node: FunctionDecl) -> object:
        # Las funciones se procesan vía build(); no anidan dentro de otra función.
        return None

    def visit_program(self, node: Program) -> object:
        return None

    # ── Expresiones: atómicas (no crean bloques) ──────────────────────────

    def visit_binary_op(self, node: BinaryOp) -> object: return None
    def visit_unary_op(self, node: UnaryOp) -> object: return None
    def visit_assign_expr(self, node: AssignExpr) -> object: return None
    def visit_call_expr(self, node: CallExpr) -> object: return None
    def visit_identifier(self, node: IdentifierExpr) -> object: return None
    def visit_int_literal(self, node: IntLiteral) -> object: return None
    def visit_float_literal(self, node: FloatLiteral) -> object: return None
    def visit_string_literal(self, node: StringLiteral) -> object: return None
    def visit_bool_literal(self, node: BoolLiteral) -> object: return None
    def visit_null_literal(self, node: NullLiteral) -> object: return None
