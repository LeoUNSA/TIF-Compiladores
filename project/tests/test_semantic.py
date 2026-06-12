"""
Tests del Analizador Semántico de MiniLang.

Cada test compila una fuente hasta el AST y ejecuta SemanticAnalyzer,
verificando que los programas válidos no produzcan errores y que cada clase
de error semántico se detecte con el mensaje y la posición esperados.
"""

import pytest

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.semantic.symbols import Symbol, SymbolTable


# ── Helpers ───────────────────────────────────────────────────────────────────

def analyze(source: str):
    """Lex + parse + análisis semántico. Devuelve (program, errores)."""
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(program)
    return program, errors, analyzer


def errors_of(source: str):
    return analyze(source)[1]


def messages(source: str):
    return [e.args[0] for e in errors_of(source)]


# ── Programas válidos ─────────────────────────────────────────────────────────

VALID_HELLO = '''
func void main() {
    string nombre = "Mundo";
    print("Hola, ", nombre, "!");
}
'''

VALID_FACTORIAL = '''
func int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}
func void main() {
    int numero = 10;
    int resultado = factorial(numero);
    print("factorial: ", resultado);
}
'''

VALID_CONTROL_FLOW = '''
func int suma_pares(int limite) {
    int suma = 0;
    int i = 0;
    while (i <= limite) {
        if (i % 2 != 0) {
            i += 1;
            continue;
        }
        suma += i;
        i += 1;
    }
    return suma;
}
func void main() {
    for (int k = 0; k < 5; k += 1) {
        if (k == 3) { break; }
    }
}
'''


@pytest.mark.parametrize("src", [VALID_HELLO, VALID_FACTORIAL, VALID_CONTROL_FLOW])
def test_programas_validos_sin_errores(src):
    assert errors_of(src) == []


def test_expresiones_decoradas_con_tipo():
    src = 'func void main() { int x = 1 + 2; bool b = 1 < 2; }'
    program, errors, _ = analyze(src)
    assert errors == []
    main = program.body[0]
    x_decl = main.body.body[0]
    b_decl = main.body.body[1]
    assert x_decl.initializer.inferred_type == "int"
    assert b_decl.initializer.inferred_type == "bool"


# ── Errores: declaraciones ────────────────────────────────────────────────────

def test_variable_no_declarada():
    msgs = messages('func void main() { print(x); }')
    assert any("no declarada" in m and "x" in m for m in msgs)


def test_redeclaracion_misma_ambito():
    msgs = messages('func void main() { int x = 1; int x = 2; }')
    assert any("ya declarada" in m for m in msgs)


def test_redeclaracion_en_ambito_anidado_permitida():
    src = 'func void main() { int x = 1; { int x = 2; print(x); } }'
    assert errors_of(src) == []


def test_funcion_duplicada():
    src = 'func void f() {} func int f() { return 1; } func void main() {}'
    assert any("ya declarada" in m for m in messages(src))


def test_var_void_prohibida():
    msgs = messages('func void main() { void v; }')
    assert any("void" in m for m in msgs)


# ── Errores: tipos ────────────────────────────────────────────────────────────

def test_init_tipo_incompatible():
    msgs = messages('func void main() { int x = "hola"; }')
    assert any("string" in m and "int" in m for m in msgs)


def test_sin_coercion_int_a_float():
    # Estricto: int NO se promueve a float.
    msgs = messages('func void main() { float y = 3; }')
    assert any("int" in m and "float" in m for m in msgs)


def test_suma_tipos_incompatibles():
    msgs = messages('func void main() { string s = "a"; int n = 1; int r = s + n; }')
    assert any("'+'" in m for m in msgs)


def test_modulo_requiere_int():
    msgs = messages('func void main() { float a = 1.0; float b = 2.0; float c = a % b; }')
    assert any("'%'" in m for m in msgs)


def test_logico_requiere_bool():
    msgs = messages('func void main() { int a = 1; bool r = a && a; }')
    assert any("'&&'" in m for m in msgs)


def test_negacion_requiere_bool():
    msgs = messages('func void main() { int a = 1; bool r = !a; }')
    assert any("'!'" in m for m in msgs)


def test_comparacion_tipos_distintos():
    msgs = messages('func void main() { bool r = 1 == "x"; }')
    assert any("comparar" in m for m in msgs)


def test_asignacion_a_no_declarada():
    msgs = messages('func void main() { x = 5; }')
    assert any("no declarada" in m for m in msgs)


def test_asignacion_compuesta_no_numerica():
    msgs = messages('func void main() { string s = "a"; s += 1; }')
    assert any("+=" in m for m in msgs)


# ── Errores: funciones ────────────────────────────────────────────────────────

def test_llamada_funcion_no_declarada():
    msgs = messages('func void main() { int x = foo(1); }')
    assert any("no declarada" in m and "foo" in m for m in msgs)


def test_aridad_incorrecta():
    src = 'func int f(int a, int b) { return a; } func void main() { int x = f(1); }'
    assert any("argumento" in m for m in messages(src))


def test_tipo_argumento_incorrecto():
    src = 'func int f(int a) { return a; } func void main() { int x = f("s"); }'
    assert any("Argumento" in m for m in messages(src))


def test_retorno_tipo_incompatible():
    msgs = messages('func int f() { return "x"; } func void main() {}')
    assert any("retorno" in m.lower() for m in msgs)


def test_void_no_retorna_valor():
    msgs = messages('func void f() { return 1; } func void main() {}')
    assert any("void" in m for m in msgs)


def test_llamada_hacia_adelante_valida():
    # main llama a una función declarada después: el pre-pase debe permitirlo.
    src = 'func void main() { int x = tardia(); } func int tardia() { return 1; }'
    assert errors_of(src) == []


# ── Errores: flujo de control ─────────────────────────────────────────────────

def test_break_fuera_de_bucle():
    msgs = messages('func void main() { break; }')
    assert any("break" in m for m in msgs)


def test_continue_fuera_de_bucle():
    msgs = messages('func void main() { continue; }')
    assert any("continue" in m for m in msgs)


def test_break_dentro_de_bucle_valido():
    src = 'func void main() { while (true) { break; } }'
    assert errors_of(src) == []


def test_condicion_if_no_booleana():
    msgs = messages('func void main() { int x = 1; if (x) { print(x); } }')
    assert any("if" in m and "bool" in m for m in msgs)


def test_condicion_while_no_booleana():
    msgs = messages('func void main() { while (1) { break; } }')
    assert any("while" in m and "bool" in m for m in msgs)


# ── Recolección de múltiples errores ──────────────────────────────────────────

def test_recolecta_multiples_errores():
    # No aborta en el primero: debe reportar varios.
    src = 'func void main() { int x = "s"; print(indef); break; }'
    assert len(errors_of(src)) >= 3


def test_posicion_en_error():
    errs = errors_of('func void main() {\n    int x = "s";\n}')
    assert errs[0].line == 2


# ── Tabla de símbolos (unidad) ────────────────────────────────────────────────

def test_scope_resolve_en_padre():
    table = SymbolTable()
    table.define(Symbol(name="g", kind="var", type="int"))
    table.push_scope("block")
    assert table.resolve("g") is not None       # visible desde el hijo
    assert table.resolve_local("g") is None     # pero no es local


def test_scope_define_duplicado():
    table = SymbolTable()
    assert table.define(Symbol(name="a", kind="var", type="int")) is True
    assert table.define(Symbol(name="a", kind="var", type="int")) is False
