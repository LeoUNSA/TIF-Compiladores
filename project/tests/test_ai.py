"""
Tests de la capa de IA (sin red).

Usan un cliente falso que captura el prompt en lugar de llamar a Ollama, de modo
que se verifica la SELECCIÓN DE CONTEXTO y el enrutado de consultas sin depender
del LLM. La generación real con Ollama se prueba manualmente vía la CLI.
"""

import pytest

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.cfg.builder import CFGBuilder
from src.serialize.document import serialize_program
from src.ai.assistant import Assistant
from src.ai import context


# ── Cliente falso ─────────────────────────────────────────────────────────────

class FakeClient:
    """Captura (prompt, system) y devuelve una respuesta fija."""
    def __init__(self, reply="RESPUESTA"):
        self.reply = reply
        self.prompt = None
        self.system = None

    def generate(self, prompt, system=None):
        self.prompt = prompt
        self.system = system
        return self.reply


# ── Helpers ───────────────────────────────────────────────────────────────────

def doc_of(source: str) -> dict:
    program = Parser(Lexer(source).tokenize()).parse()
    errors  = SemanticAnalyzer().analyze(program)
    cfgs    = CFGBuilder().build(program)
    return serialize_program(program, errors=errors, cfgs=cfgs)


FACTORIAL = '''
func int factorial(int n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
func void main() {
    int resultado = factorial(10);
    print(resultado);
}
'''


# ── Selección de contexto ─────────────────────────────────────────────────────

def test_find_function():
    doc = doc_of(FACTORIAL)
    assert context.find_function(doc, "factorial")["return_type"] == "int"
    assert context.find_function(doc, "noexiste") is None


def test_find_variable_con_inicializador():
    doc = doc_of(FACTORIAL)
    hits = context.find_variable(doc, "resultado")
    assert len(hits) == 1
    assert hits[0]["funcion"] == "main"
    assert hits[0]["type"] == "int"
    # El inicializador (llamada a factorial) viene del AST.
    assert hits[0]["inicializador"]["node"] == "CallExpr"


def test_find_variable_parametro():
    doc = doc_of(FACTORIAL)
    hits = context.find_variable(doc, "n")
    assert any(h["funcion"] == "factorial" for h in hits)


def test_structure_resumen():
    doc = doc_of(FACTORIAL)
    s = context.structure(doc)
    nombres = [f["nombre"] for f in s["funciones"]]
    assert nombres == ["factorial", "main"]
    fact = s["funciones"][0]
    assert fact["ramas_if"] >= 1            # tiene un if


def test_diagnostics_with_source():
    doc = doc_of('func void main() { int x = "s"; }')
    ctx = context.diagnostics_with_source(doc, 'func void main() { int x = "s"; }')
    assert len(ctx["diagnosticos"]) == 1
    assert "x" in ctx["diagnosticos"][0]["codigo"]


# ── Enrutado del Assistant ────────────────────────────────────────────────────

def test_explain_function_arma_prompt():
    doc = doc_of(FACTORIAL)
    client = FakeClient()
    out = Assistant(client).explain_function(doc, "factorial")
    assert out == "RESPUESTA"
    assert "factorial" in client.prompt
    assert client.system is not None and "SemanticC" in client.system


def test_explain_function_inexistente():
    doc = doc_of(FACTORIAL)
    with pytest.raises(ValueError):
        Assistant(FakeClient()).explain_function(doc, "fantasma")


def test_describe_incluye_variable_en_prompt():
    doc = doc_of(FACTORIAL)
    client = FakeClient()
    Assistant(client).describe(doc, "resultado")
    assert "resultado" in client.prompt


def test_navigate_incluye_funciones():
    doc = doc_of(FACTORIAL)
    client = FakeClient()
    Assistant(client).navigate(doc)
    assert "factorial" in client.prompt and "main" in client.prompt


def test_explain_error_incluye_diagnostico():
    src = 'func void main() { int x = "s"; }'
    doc = doc_of(src)
    client = FakeClient()
    Assistant(client).explain_error(doc, src)
    assert "string" in client.prompt        # mensaje del diagnóstico
