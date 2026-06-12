"""
Tests de la serialización a JSON (documento semántico para la capa de IA).

Verifican que el documento sea JSON-válido y que contenga el AST decorado con
tipos, la tabla de símbolos por función, el CFG y los diagnósticos.
"""

import json

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.cfg.builder import CFGBuilder
from src.serialize.json_serializer import JsonSerializer
from src.serialize.document import serialize_program


# ── Helpers ───────────────────────────────────────────────────────────────────

def document(source: str) -> dict:
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    errors  = SemanticAnalyzer().analyze(program)
    cfgs    = CFGBuilder().build(program)
    return serialize_program(program, errors=errors, cfgs=cfgs)


FACTORIAL = '''
func int factorial(int n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
func void main() {
    int numero = 10;
    int resultado = factorial(numero);
    print("r: ", resultado);
}
'''


# ── Estructura del documento ──────────────────────────────────────────────────

def test_documento_es_json_serializable():
    doc = document(FACTORIAL)
    # No debe lanzar: todo es primitivo.
    text = json.dumps(doc, ensure_ascii=False)
    assert json.loads(text) == doc


def test_campos_de_nivel_superior():
    doc = document(FACTORIAL)
    assert doc["language"] == "MiniLang"
    assert {"functions", "globals", "diagnostics"} <= set(doc)


def test_funciones_listadas():
    doc = document(FACTORIAL)
    names = [f["name"] for f in doc["functions"]]
    assert names == ["factorial", "main"]


def test_firma_de_funcion():
    doc = document(FACTORIAL)
    fact = doc["functions"][0]
    assert fact["return_type"] == "int"
    assert fact["params"] == [
        {"name": "n", "type": "int", "kind": "param",
         "line": fact["params"][0]["line"], "column": fact["params"][0]["column"]}
    ]


def test_locales_recolectados_con_tipo():
    doc = document(FACTORIAL)
    main = doc["functions"][1]
    locals_ = {l["name"]: l["type"] for l in main["locals"]}
    assert locals_ == {"numero": "int", "resultado": "int"}


# ── AST decorado con tipos ────────────────────────────────────────────────────

def test_expresiones_llevan_tipo_inferido():
    doc = document('func void main() { int x = 1 + 2; }')
    body = doc["functions"][0]["ast"]["body"]
    var_decl = body[0]
    init = var_decl["initializer"]
    assert init["node"] == "BinaryOp"
    assert init["type"] == "int"
    assert init["left"]["type"] == "int"


def test_serializer_directo_sobre_nodo():
    tokens  = Lexer('func void main() { bool b = 1 < 2; }').tokenize()
    program = Parser(tokens).parse()
    SemanticAnalyzer().analyze(program)
    out = JsonSerializer().serialize(program)
    assert out["node"] == "Program"
    cmp = out["body"][0]["body"]["body"][0]["initializer"]
    assert cmp["node"] == "BinaryOp" and cmp["type"] == "bool"


# ── CFG incrustado ────────────────────────────────────────────────────────────

def test_cfg_incrustado_por_funcion():
    doc = document(FACTORIAL)
    fact = doc["functions"][0]
    assert "cfg" in fact
    cfg = fact["cfg"]
    assert isinstance(cfg["entry"], int) and isinstance(cfg["exit"], int)
    assert len(cfg["blocks"]) >= 2
    # Cada arista referencia un id de bloque válido.
    ids = {b["id"] for b in cfg["blocks"]}
    for b in cfg["blocks"]:
        for e in b["successors"]:
            assert e["to"] in ids


# ── Diagnósticos ──────────────────────────────────────────────────────────────

def test_diagnosticos_vacios_si_valido():
    assert document(FACTORIAL)["diagnostics"] == []


def test_diagnosticos_incluyen_errores_semanticos():
    doc = document('func void main() { int x = "hola"; print(indef); }')
    diags = doc["diagnostics"]
    assert len(diags) == 2
    assert all(d["phase"] == "semantic" for d in diags)
    assert all("line" in d and "message" in d for d in diags)
