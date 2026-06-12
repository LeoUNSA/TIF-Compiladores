"""
Tests del constructor del Grafo de Flujo de Control (CFG) de MiniLang.

Verifican la estructura del grafo: bloques entry/exit, ramas de if/else,
aristas de retroceso en bucles, y los destinos de break/continue.
"""

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.cfg.builder import CFGBuilder
from src.cfg.blocks import format_cfg


# ── Helpers ───────────────────────────────────────────────────────────────────

def build(source: str):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return CFGBuilder().build(program)


def first_cfg(source: str):
    return build(source)[0]


def succ_labels(block):
    return {(e.target.label, e.label) for e in block.successors}


def reaches(start, target):
    """¿Existe un camino dirigido de `start` a `target`?"""
    seen, stack = set(), [start]
    while stack:
        b = stack.pop()
        if b is target:
            return True
        if b.id in seen:
            continue
        seen.add(b.id)
        stack.extend(e.target for e in b.successors)
    return False


# ── Estructura básica ─────────────────────────────────────────────────────────

def test_un_cfg_por_funcion():
    cfgs = build('func void a() {} func int b() { return 1; } func void main() {}')
    assert [c.function_name for c in cfgs] == ["a", "b", "main"]


def test_entry_y_exit_existen():
    cfg = first_cfg('func void main() { int x = 1; }')
    assert cfg.entry is not None and cfg.exit is not None
    assert cfg.entry.label == "entry" and cfg.exit.label == "exit"


def test_programa_lineal_entry_llega_a_exit():
    cfg = first_cfg('func void main() { int x = 1; int y = 2; print(x, y); }')
    assert reaches(cfg.entry, cfg.exit)
    # Las tres sentencias caen en el bloque de entrada (flujo lineal).
    assert len(cfg.entry.statements) == 3


def test_caida_implicita_conecta_a_exit():
    cfg = first_cfg('func void main() { int x = 1; }')
    assert any(e.target is cfg.exit for e in cfg.entry.successors)


# ── if / else ─────────────────────────────────────────────────────────────────

def test_if_simple_genera_rama_true_false():
    cfg = first_cfg('func void main() { int x = 1; if (x == 1) { print(x); } }')
    labels = {e.label for e in cfg.entry.successors}
    assert "true" in labels and "false" in labels


def test_if_guarda_condicion_en_bloque():
    cfg = first_cfg('func void main() { int x = 1; if (x == 1) { print(x); } }')
    assert cfg.entry.condition is not None


def test_if_else_ambas_ramas_convergen():
    src = 'func void main() { int x = 1; if (x==1) { print(1); } else { print(2); } }'
    cfg = first_cfg(src)
    merges = [b for b in cfg.blocks if b.label == "if.end"]
    assert len(merges) == 1
    merge = merges[0]
    then_b = [b for b in cfg.blocks if b.label == "if.then"][0]
    else_b = [b for b in cfg.blocks if b.label == "if.else"][0]
    assert reaches(then_b, merge) and reaches(else_b, merge)


def test_if_else_con_return_en_ambas_no_genera_merge():
    src = ('func int f(int x) { if (x==1) { return 1; } else { return 2; } }'
           ' func void main() {}')
    cfg = build(src)[0]
    assert not any(b.label == "if.end" for b in cfg.blocks)


# ── while ─────────────────────────────────────────────────────────────────────

def test_while_tiene_arista_de_retroceso():
    src = 'func void main() { int i = 0; while (i < 5) { i += 1; } }'
    cfg = first_cfg(src)
    header = [b for b in cfg.blocks if b.label == "while.cond"][0]
    body   = [b for b in cfg.blocks if b.label == "while.body"][0]
    # body vuelve al header (back-edge); header ramifica a body/exit.
    assert any(e.target is header for e in body.successors)
    assert ("while.body", "true") in succ_labels(header)
    assert ("while.end", "false") in succ_labels(header)


def test_while_break_va_al_exit_del_bucle():
    src = 'func void main() { while (true) { break; } }'
    cfg = first_cfg(src)
    body = [b for b in cfg.blocks if b.label == "while.body"][0]
    end  = [b for b in cfg.blocks if b.label == "while.end"][0]
    assert any(e.target is end and e.label == "break" for e in body.successors)


def test_while_continue_va_al_header():
    src = 'func void main() { int i = 0; while (i < 5) { continue; } }'
    cfg = first_cfg(src)
    header = [b for b in cfg.blocks if b.label == "while.cond"][0]
    body   = [b for b in cfg.blocks if b.label == "while.body"][0]
    assert any(e.target is header and e.label == "continue" for e in body.successors)


# ── for ───────────────────────────────────────────────────────────────────────

def test_for_continue_va_al_update():
    src = 'func void main() { for (int k=0; k<5; k+=1) { continue; } }'
    cfg = first_cfg(src)
    update = [b for b in cfg.blocks if b.label == "for.update"][0]
    body   = [b for b in cfg.blocks if b.label == "for.body"][0]
    assert any(e.target is update and e.label == "continue" for e in body.successors)


def test_for_update_vuelve_a_la_condicion():
    src = 'func void main() { for (int k=0; k<5; k+=1) { print(k); } }'
    cfg = first_cfg(src)
    header = [b for b in cfg.blocks if b.label == "for.cond"][0]
    update = [b for b in cfg.blocks if b.label == "for.update"][0]
    assert any(e.target is header for e in update.successors)


# ── return ────────────────────────────────────────────────────────────────────

def test_return_termina_el_flujo():
    # La sentencia tras un return queda en un bloque inalcanzable (sin sucesores
    # desde el bloque del return salvo la arista al exit).
    src = 'func int f() { return 1; int x = 2; } func void main() {}'
    cfg = build(src)[0]
    # entry contiene el return y conecta SOLO al exit.
    assert all(e.target is cfg.exit for e in cfg.entry.successors)


# ── Formateo ──────────────────────────────────────────────────────────────────

def test_format_cfg_legible():
    cfg = first_cfg('func void main() { int x = 1; if (x==1) { print(x); } }')
    out = format_cfg(cfg)
    assert "CFG de 'main'" in out
    assert "[entry]" in out and "[exit]" in out
    assert "→" in out
