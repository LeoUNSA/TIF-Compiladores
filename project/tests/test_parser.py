"""Tests del analizador sintáctico (Parser) de MiniLang."""

import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.parser.ast_nodes import (
    Program, FunctionDecl, VarDecl, Block, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ReadStmt, ExprStmt,
    BinaryOp, UnaryOp, AssignExpr, CallExpr, IdentifierExpr,
    IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral,
)
from src.errors import ParseError


# ── Helper ────────────────────────────────────────────────────────────────────

def parse(source: str) -> Program:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# ── Programa vacío ────────────────────────────────────────────────────────────

class TestProgram:
    def test_empty_program(self):
        prog = parse("")
        assert isinstance(prog, Program)
        assert prog.body == []


# ── Declaraciones de variables ────────────────────────────────────────────────

class TestVarDecl:
    def test_int_no_init(self):
        prog  = parse("int x;")
        decl  = prog.body[0]
        assert isinstance(decl, VarDecl)
        assert decl.type_name    == "int"
        assert decl.name         == "x"
        assert decl.initializer is None

    def test_int_with_init(self):
        prog  = parse("int x = 42;")
        decl  = prog.body[0]
        assert isinstance(decl.initializer, IntLiteral)
        assert decl.initializer.value == 42

    def test_float_init(self):
        prog = parse("float pi = 3.14;")
        decl = prog.body[0]
        assert decl.type_name == "float"
        assert isinstance(decl.initializer, FloatLiteral)

    def test_string_init(self):
        prog = parse('string s = "hola";')
        decl = prog.body[0]
        assert isinstance(decl.initializer, StringLiteral)
        assert decl.initializer.value == "hola"

    def test_bool_init(self):
        prog = parse("bool b = true;")
        decl = prog.body[0]
        assert isinstance(decl.initializer, BoolLiteral)
        assert decl.initializer.value is True

    def test_null_init(self):
        prog = parse("int n = null;")
        decl = prog.body[0]
        assert isinstance(decl.initializer, NullLiteral)


# ── Declaraciones de funciones ────────────────────────────────────────────────

class TestFunctionDecl:
    def test_void_no_params(self):
        prog = parse("func void main() {}")
        fn   = prog.body[0]
        assert isinstance(fn, FunctionDecl)
        assert fn.name        == "main"
        assert fn.return_type == "void"
        assert fn.params      == []

    def test_int_two_params(self):
        prog = parse("func int suma(int a, int b) { return a + b; }")
        fn   = prog.body[0]
        assert fn.name        == "suma"
        assert fn.return_type == "int"
        assert len(fn.params) == 2
        assert fn.params[0].name      == "a"
        assert fn.params[0].type_name == "int"
        assert fn.params[1].name      == "b"

    def test_function_body_is_block(self):
        prog = parse("func void f() { int x = 1; }")
        fn   = prog.body[0]
        assert isinstance(fn.body, Block)
        assert len(fn.body.body) == 1


# ── Sentencias de control ─────────────────────────────────────────────────────

class TestControlFlow:
    def test_if_only(self):
        prog = parse("if (x) { }")
        stmt = prog.body[0]
        assert isinstance(stmt, IfStmt)
        assert stmt.else_branch is None

    def test_if_else(self):
        prog = parse("if (x) { } else { }")
        stmt = prog.body[0]
        assert isinstance(stmt, IfStmt)
        assert isinstance(stmt.else_branch, Block)

    def test_if_else_if(self):
        prog = parse("if (a) { } else if (b) { }")
        stmt = prog.body[0]
        assert isinstance(stmt.else_branch, IfStmt)

    def test_while(self):
        prog = parse("while (x > 0) { x -= 1; }")
        stmt = prog.body[0]
        assert isinstance(stmt, WhileStmt)

    def test_for(self):
        prog = parse("for (int i = 0; i < 10; i += 1) { }")
        stmt = prog.body[0]
        assert isinstance(stmt, ForStmt)
        assert isinstance(stmt.init, VarDecl)
        assert isinstance(stmt.condition, BinaryOp)
        assert isinstance(stmt.update, AssignExpr)

    def test_break(self):
        prog = parse("break;")
        assert isinstance(prog.body[0], BreakStmt)

    def test_continue(self):
        prog = parse("continue;")
        assert isinstance(prog.body[0], ContinueStmt)

    def test_return_no_value(self):
        prog = parse("return;")
        stmt = prog.body[0]
        assert isinstance(stmt, ReturnStmt)
        assert stmt.value is None

    def test_return_with_value(self):
        prog = parse("return 42;")
        stmt = prog.body[0]
        assert isinstance(stmt.value, IntLiteral)


# ── Sentencias I/O ────────────────────────────────────────────────────────────

class TestIOStatements:
    def test_print_single(self):
        prog = parse('print("hola");')
        stmt = prog.body[0]
        assert isinstance(stmt, PrintStmt)
        assert len(stmt.args) == 1

    def test_print_multiple(self):
        prog = parse('print("a", x, 42);')
        stmt = prog.body[0]
        assert len(stmt.args) == 3

    def test_read_single(self):
        prog = parse("read(x);")
        stmt = prog.body[0]
        assert isinstance(stmt, ReadStmt)
        assert stmt.targets == ["x"]

    def test_read_multiple(self):
        prog = parse("read(a, b, c);")
        stmt = prog.body[0]
        assert stmt.targets == ["a", "b", "c"]


# ── Expresiones ───────────────────────────────────────────────────────────────

class TestExpressions:
    def _expr(self, source: str):
        """Parsea una expresión envuelta en ExprStmt."""
        prog = parse(source + ";")
        return prog.body[0].expr

    def test_integer_literal(self):
        e = self._expr("7")
        assert isinstance(e, IntLiteral)
        assert e.value == 7

    def test_float_literal(self):
        e = self._expr("2.5")
        assert isinstance(e, FloatLiteral)

    def test_bool_literal(self):
        e = self._expr("false")
        assert isinstance(e, BoolLiteral)
        assert e.value is False

    def test_null_literal(self):
        e = self._expr("null")
        assert isinstance(e, NullLiteral)

    def test_identifier(self):
        e = self._expr("miVar")
        assert isinstance(e, IdentifierExpr)
        assert e.name == "miVar"

    def test_binary_add(self):
        e = self._expr("1 + 2")
        assert isinstance(e, BinaryOp)
        assert e.operator == "+"
        assert isinstance(e.left,  IntLiteral)
        assert isinstance(e.right, IntLiteral)

    def test_binary_precedence(self):
        # 1 + 2 * 3  →  1 + (2 * 3)
        e = self._expr("1 + 2 * 3")
        assert isinstance(e, BinaryOp)
        assert e.operator == "+"
        assert isinstance(e.right, BinaryOp)
        assert e.right.operator == "*"

    def test_grouping(self):
        # (1 + 2) * 3  →  (* (+ 1 2) 3)
        e = self._expr("(1 + 2) * 3")
        assert e.operator == "*"
        assert e.left.operator == "+"

    def test_unary_negation(self):
        e = self._expr("-x")
        assert isinstance(e, UnaryOp)
        assert e.operator == "-"

    def test_unary_not(self):
        e = self._expr("!flag")
        assert isinstance(e, UnaryOp)
        assert e.operator == "!"

    def test_assignment(self):
        e = self._expr("x = 5")
        assert isinstance(e, AssignExpr)
        assert e.name     == "x"
        assert e.operator == "="

    def test_compound_assignment(self):
        e = self._expr("x += 3")
        assert isinstance(e, AssignExpr)
        assert e.operator == "+="

    def test_call_no_args(self):
        e = self._expr("foo()")
        assert isinstance(e, CallExpr)
        assert e.name      == "foo"
        assert e.arguments == []

    def test_call_with_args(self):
        e = self._expr("max(a, b)")
        assert isinstance(e, CallExpr)
        assert len(e.arguments) == 2

    def test_logic_and(self):
        e = self._expr("a && b")
        assert isinstance(e, BinaryOp)
        assert e.operator == "&&"

    def test_logic_or(self):
        e = self._expr("a || b")
        assert isinstance(e, BinaryOp)
        assert e.operator == "||"

    def test_comparison(self):
        e = self._expr("x >= 10")
        assert isinstance(e, BinaryOp)
        assert e.operator == ">="


# ── Errores sintácticos ───────────────────────────────────────────────────────

class TestParseErrors:
    def test_missing_semicolon(self):
        with pytest.raises(ParseError):
            parse("int x = 5")

    def test_missing_rparen_if(self):
        with pytest.raises(ParseError):
            parse("if (x { }")

    def test_missing_rbrace(self):
        with pytest.raises(ParseError):
            parse("func void f() {")

    def test_invalid_expression(self):
        with pytest.raises(ParseError):
            parse(";")

    def test_func_missing_name(self):
        with pytest.raises(ParseError):
            parse("func int () {}")


# ── Programa completo: factorial ──────────────────────────────────────────────

class TestFullProgram:
    FACTORIAL = """
    func int factorial(int n) {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }

    func void main() {
        int numero = 10;
        int resultado = factorial(numero);
        print("Resultado: ", resultado);
    }
    """

    def test_factorial_parses(self):
        prog = parse(self.FACTORIAL)
        assert len(prog.body) == 2
        fn1, fn2 = prog.body
        assert isinstance(fn1, FunctionDecl)
        assert isinstance(fn2, FunctionDecl)
        assert fn1.name == "factorial"
        assert fn2.name == "main"

    def test_factorial_param(self):
        prog = parse(self.FACTORIAL)
        fn   = prog.body[0]
        assert fn.params[0].name      == "n"
        assert fn.params[0].type_name == "int"
