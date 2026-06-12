#!/usr/bin/env python3
"""
main.py — Punto de entrada del Compilador MiniLang.

Uso:
    python main.py <archivo.ml>           # AST + análisis semántico
    python main.py --tokens <archivo.ml>  # muestra solo los tokens
    python main.py --symbols <archivo.ml> # AST + semántico + tabla de símbolos
    python main.py --cfg <archivo.ml>     # AST + semántico + CFG por función
    python main.py --json <archivo.ml>    # documento semántico (JSON) para la IA
    python main.py --help

    # Consultas en lenguaje natural (requieren Ollama corriendo):
    python main.py --explain-function factorial archivo.ml
    python main.py --describe resultado archivo.ml
    python main.py --explain-error archivo.ml
    python main.py --navigate archivo.ml

Este frontend es el prototipo base del "Compilador Aumentado con IA"
descrito en el paper: expone el AST decorado con tipos, la tabla de
símbolos y el CFG como representaciones accesibles que la capa de IA
consulta para generar explicaciones en lenguaje natural.
"""

import argparse
import json
import sys
from pathlib import Path

# Aseguramos que el directorio padre esté en el path al ejecutar directamente
sys.path.insert(0, str(Path(__file__).parent))

from src.errors import LexerError, ParseError
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.parser.ast_printer import ASTPrinter
from src.semantic.analyzer import SemanticAnalyzer
from src.cfg.builder import CFGBuilder
from src.cfg.blocks import format_cfg
from src.serialize.document import serialize_program


# ─────────────────────────────────────────────────────────────────────────────

def compile_source(
    source: str,
    filename: str,
    show_tokens: bool = False,
    show_symbols: bool = False,
    show_cfg: bool = False,
    emit_json: bool = False,
) -> int:
    """
    Ejecuta las fases léxica, sintáctica y semántica sobre `source`.

    Devuelve 0 si tuvo éxito, 1 si hubo errores.
    """
    # ── Fase 1: Análisis Léxico ───────────────────────────────────────────
    try:
        lexer  = Lexer(source)
        tokens = lexer.tokenize()
    except LexerError as e:
        print(f"{filename}: {e}", file=sys.stderr)
        return 1

    if show_tokens:
        print(f"── Tokens de '{filename}' ──────────────────────────────")
        for tok in tokens:
            print(f"  {tok}")
        print()
        return 0

    # ── Fase 2: Análisis Sintáctico ───────────────────────────────────────
    try:
        parser  = Parser(tokens)
        program = parser.parse()
    except ParseError as e:
        print(f"{filename}: {e}", file=sys.stderr)
        return 1

    # ── Salida JSON: documento semántico para la capa de IA ───────────────
    # Se emite SIEMPRE (con o sin errores semánticos): los diagnósticos van
    # dentro del JSON, útil para consultas tipo --explain-error.
    if emit_json:
        errors = SemanticAnalyzer().analyze(program)
        cfgs   = CFGBuilder().build(program)
        doc    = serialize_program(program, errors=errors, cfgs=cfgs)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    # ── Visualización del AST ─────────────────────────────────────────────
    printer = ASTPrinter()
    ast_str = printer.print(program)

    print(f"── AST de '{filename}' ─────────────────────────────────")
    print(ast_str)

    # ── Fase 3: Análisis Semántico ────────────────────────────────────────
    analyzer = SemanticAnalyzer()
    errors   = analyzer.analyze(program)

    if errors:
        print(f"── Errores semánticos en '{filename}' ──────────────────",
              file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    print("── Análisis semántico: ✓ sin errores ───────────────────")

    if show_symbols:
        _dump_symbols(analyzer.table.global_scope)

    # ── Fase 4: Grafo de Flujo de Control ─────────────────────────────────
    if show_cfg:
        cfgs = CFGBuilder().build(program)
        print(f"── CFG de '{filename}' ─────────────────────────────────")
        for cfg in cfgs:
            print(format_cfg(cfg))
            print()

    return 0


def _dump_symbols(scope, depth: int = 0) -> None:
    """Imprime la tabla de símbolos del ámbito global de forma indentada."""
    if depth == 0:
        print("── Tabla de Símbolos (ámbito global) ───────────────────")
    pad = "  " * (depth + 1)
    for sym in scope.symbols.values():
        print(f"{pad}{sym}  @ línea {sym.line}, col {sym.column}")


# ─────────────────────────────────────────────────────────────────────────────
# Capa de IA (consultas en lenguaje natural)
# ─────────────────────────────────────────────────────────────────────────────

def run_ai_query(source: str, filename: str, args) -> int:
    """Construye el documento semántico y responde la consulta vía LLM (Ollama)."""
    # La capa de IA se importa de forma perezosa: el núcleo no depende de ella.
    from src.ai.client import OllamaClient, OllamaError, DEFAULT_MODEL
    from src.ai.assistant import Assistant

    # Fases 1-2: necesitamos un AST válido para consultar.
    try:
        tokens  = Lexer(source).tokenize()
        program = Parser(tokens).parse()
    except (LexerError, ParseError) as e:
        print(f"{filename}: {e}", file=sys.stderr)
        return 1

    errors = SemanticAnalyzer().analyze(program)
    cfgs   = CFGBuilder().build(program)
    doc    = serialize_program(program, errors=errors, cfgs=cfgs)

    model  = args.model or DEFAULT_MODEL
    client = OllamaClient(model=model)
    if not client.available():
        print(f"Error: no se pudo contactar Ollama en {client.host}. "
              "¿Está corriendo `ollama serve`?", file=sys.stderr)
        return 1
    if not client.has_model():
        print(f"Error: el modelo '{model}' no está descargado. "
              f"Ejecuta:  ollama pull {model}", file=sys.stderr)
        return 1

    assistant = Assistant(client)
    try:
        if args.explain_function:
            answer = assistant.explain_function(doc, args.explain_function)
        elif args.describe:
            answer = assistant.describe(doc, args.describe)
        elif args.explain_error:
            answer = assistant.explain_error(doc, source)
        else:  # args.navigate
            answer = assistant.navigate(doc)
    except ValueError as e:               # objetivo de consulta inexistente
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except OllamaError as e:
        print(f"Error de Ollama: {e}", file=sys.stderr)
        return 1

    print(answer)
    return 0


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        prog="minilang",
        description="Compilador MiniLang — prototipo del Compilador Aumentado con IA",
    )
    ap.add_argument("file", help="Archivo fuente MiniLang (.ml)")
    ap.add_argument(
        "--tokens",
        action="store_true",
        help="Mostrar solo el flujo de tokens (sin AST)",
    )
    ap.add_argument(
        "--symbols",
        action="store_true",
        help="Mostrar la tabla de símbolos del ámbito global tras el análisis",
    )
    ap.add_argument(
        "--cfg",
        action="store_true",
        help="Mostrar el Grafo de Flujo de Control (un CFG por función)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emitir el documento semántico (AST+símbolos+CFG+diagnósticos) en JSON",
    )

    ai = ap.add_argument_group("Consultas en lenguaje natural (capa de IA, Ollama)")
    ai.add_argument("--explain-function", metavar="NOMBRE",
                    help="Explicar qué hace una función")
    ai.add_argument("--describe", metavar="VARIABLE",
                    help="Describir una variable en su contexto")
    ai.add_argument("--explain-error", action="store_true",
                    help="Explicar los errores del compilador en lenguaje accesible")
    ai.add_argument("--navigate", action="store_true",
                    help="Describir la estructura general del programa")
    ai.add_argument("--model", metavar="MODELO",
                    help="Modelo de Ollama a usar (default: $MINILANG_MODEL o llama3.2:3b)")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: archivo no encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    source = path.read_text(encoding="utf-8")

    # Si se pidió una consulta en lenguaje natural, va por la capa de IA.
    if (args.explain_function or args.describe or args.explain_error
            or args.navigate):
        sys.exit(run_ai_query(source, str(path), args))

    exit_code = compile_source(
        source, str(path), show_tokens=args.tokens,
        show_symbols=args.symbols, show_cfg=args.cfg, emit_json=args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
