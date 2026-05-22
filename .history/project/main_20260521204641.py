#!/usr/bin/env python3
"""
main.py — Punto de entrada del Compilador MiniLang.

Uso:
    python main.py <archivo.ml>          # analiza y muestra el AST
    python main.py --tokens <archivo.ml> # muestra solo los tokens
    python main.py --help

Este frontend es el prototipo base del "Compilador Aumentado con IA"
descrito en el paper: expone el AST como representación accesible
que la capa de IA puede consultar para generar explicaciones.
"""

import argparse
import sys
from pathlib import Path

# Aseguramos que el directorio padre esté en el path al ejecutar directamente
sys.path.insert(0, str(Path(__file__).parent))

from src.errors import LexerError, ParseError
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.parser.ast_printer import ASTPrinter


# ─────────────────────────────────────────────────────────────────────────────

def compile_source(source: str, filename: str, show_tokens: bool = False) -> int:
    """
    Ejecuta las fases léxica y sintáctica sobre `source`.

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

    # ── Visualización del AST ─────────────────────────────────────────────
    printer = ASTPrinter()
    ast_str = printer.print(program)

    print(f"── AST de '{filename}' ─────────────────────────────────")
    print(ast_str)
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
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: archivo no encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    source = path.read_text(encoding="utf-8")
    exit_code = compile_source(source, str(path), show_tokens=args.tokens)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
