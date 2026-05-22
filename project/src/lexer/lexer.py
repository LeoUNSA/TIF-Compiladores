"""
Analizador Léxico (Lexer) para MiniLang.

Transforma el texto fuente en un flujo de Token, detectando y
reportando errores léxicos con posición exacta (línea:columna).

Características:
- Comentarios de línea  // ...
- Comentarios de bloque /* ... */
- Literales enteros y flotantes
- Literales de cadena con secuencias de escape (\\n \\t \\\\ \\")
- Identificadores y palabras reservadas
- Operadores simples y compuestos (+=, ==, !=, <=, >=, ||, &&)
"""

from __future__ import annotations

from typing import List

from .tokens import KEYWORDS, Token, TokenType
from ..errors import LexerError


class Lexer:
    """Convierte código fuente MiniLang en una lista de Token."""

    def __init__(self, source: str) -> None:
        self._source:  str        = source
        self._tokens:  List[Token] = []
        self._start:   int        = 0   # inicio del lexema actual
        self._current: int        = 0   # posición de lectura
        self._line:    int        = 1
        self._line_start: int     = 0   # offset del inicio de línea actual

    # ── API pública ───────────────────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        """Realiza el análisis léxico completo y devuelve la lista de tokens."""
        while not self._at_end():
            self._start = self._current
            self._scan_token()

        self._tokens.append(
            Token(TokenType.EOF, "", None, self._line, self._column())
        )
        return self._tokens

    # ── Lectura de caracteres ─────────────────────────────────────────────

    def _at_end(self) -> bool:
        return self._current >= len(self._source)

    def _advance(self) -> str:
        ch = self._source[self._current]
        self._current += 1
        return ch

    def _peek(self) -> str:
        """Carácter actual sin consumirlo. Devuelve '\\0' al final."""
        if self._at_end():
            return "\0"
        return self._source[self._current]

    def _peek_next(self) -> str:
        """Siguiente carácter sin consumirlo."""
        if self._current + 1 >= len(self._source):
            return "\0"
        return self._source[self._current + 1]

    def _match(self, expected: str) -> bool:
        """Consume el carácter actual solo si coincide con `expected`."""
        if self._at_end() or self._source[self._current] != expected:
            return False
        self._current += 1
        return True

    def _column(self) -> int:
        return self._start - self._line_start + 1

    # ── Emisión de tokens ─────────────────────────────────────────────────

    def _add(self, type: TokenType, literal: object = None) -> None:
        lexeme = self._source[self._start:self._current]
        self._tokens.append(
            Token(type, lexeme, literal, self._line, self._column())
        )

    # ── Escáner principal ─────────────────────────────────────────────────

    def _scan_token(self) -> None:
        ch = self._advance()

        # ── Caracteres simples ────────────────────────────────────────────
        single = {
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ";": TokenType.SEMICOLON,
            ",": TokenType.COMMA,
            ".": TokenType.DOT,
            "%": TokenType.PERCENT,
        }
        if ch in single:
            self._add(single[ch])
            return

        # ── Operadores compuestos o simples ───────────────────────────────
        if ch == "!":
            self._add(TokenType.BANG_EQ if self._match("=") else TokenType.BANG)
        elif ch == "=":
            self._add(TokenType.EQ_EQ  if self._match("=") else TokenType.EQ)
        elif ch == "<":
            self._add(TokenType.LESS_EQ    if self._match("=") else TokenType.LESS)
        elif ch == ">":
            self._add(TokenType.GREATER_EQ if self._match("=") else TokenType.GREATER)
        elif ch == "+":
            self._add(TokenType.PLUS_EQ    if self._match("=") else TokenType.PLUS)
        elif ch == "-":
            self._add(TokenType.MINUS_EQ   if self._match("=") else TokenType.MINUS)
        elif ch == "*":
            self._add(TokenType.STAR_EQ    if self._match("=") else TokenType.STAR)
        elif ch == "&":
            if self._match("&"):
                self._add(TokenType.AMP_AMP)
            else:
                self._error(f"Carácter inesperado '&': ¿quiso escribir '&&'?")
        elif ch == "|":
            if self._match("|"):
                self._add(TokenType.PIPE_PIPE)
            else:
                self._error(f"Carácter inesperado '|': ¿quiso escribir '||'?")

        # ── División o comentario ─────────────────────────────────────────
        elif ch == "/":
            if self._match("/"):
                self._line_comment()
            elif self._match("*"):
                self._block_comment()
            elif self._match("="):
                self._add(TokenType.SLASH_EQ)
            else:
                self._add(TokenType.SLASH)

        # ── Espacios en blanco ────────────────────────────────────────────
        elif ch in (" ", "\r", "\t"):
            pass  # ignorar
        elif ch == "\n":
            self._line += 1
            self._line_start = self._current

        # ── Literales de cadena ───────────────────────────────────────────
        elif ch == '"':
            self._string()

        # ── Números ───────────────────────────────────────────────────────
        elif ch.isdigit():
            self._number()

        # ── Identificadores y palabras reservadas ─────────────────────────
        elif ch.isalpha() or ch == "_":
            self._identifier()

        else:
            self._error(f"Carácter inesperado: {ch!r}")

    # ── Literales de cadena ───────────────────────────────────────────────

    def _string(self) -> None:
        value_chars: list[str] = []
        while not self._at_end() and self._peek() != '"':
            ch = self._advance()
            if ch == "\n":
                self._line += 1
                self._line_start = self._current
                value_chars.append(ch)
            elif ch == "\\":
                esc = self._advance()
                escape_map = {
                    "n": "\n", "t": "\t", "r": "\r",
                    "\\": "\\", '"': '"', "'": "'", "0": "\0",
                }
                if esc in escape_map:
                    value_chars.append(escape_map[esc])
                else:
                    self._error(f"Secuencia de escape inválida: \\{esc}")
            else:
                value_chars.append(ch)

        if self._at_end():
            self._error("Cadena de texto sin cerrar")

        self._advance()  # consume la comilla de cierre "
        self._add(TokenType.STRING, "".join(value_chars))

    # ── Números ───────────────────────────────────────────────────────────

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()

        is_float = False
        if self._peek() == "." and self._peek_next().isdigit():
            is_float = True
            self._advance()  # consume "."
            while self._peek().isdigit():
                self._advance()

        lexeme = self._source[self._start:self._current]
        if is_float:
            self._add(TokenType.FLOAT, float(lexeme))
        else:
            self._add(TokenType.INTEGER, int(lexeme))

    # ── Identificadores y palabras reservadas ─────────────────────────────

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        text = self._source[self._start:self._current]
        ttype = KEYWORDS.get(text, TokenType.IDENTIFIER)

        if ttype == TokenType.BOOL:
            literal = (text == "true")
            self._add(ttype, literal)
        else:
            self._add(ttype)

    # ── Comentarios ───────────────────────────────────────────────────────

    def _line_comment(self) -> None:
        """Consume hasta el final de la línea (sin incluir el \\n)."""
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _block_comment(self) -> None:
        """Consume /* ... */ con soporte a comentarios multi-línea."""
        start_line = self._line
        start_col  = self._column()

        while not self._at_end():
            if self._peek() == "\n":
                self._advance()
                self._line += 1
                self._line_start = self._current
            elif self._peek() == "*" and self._peek_next() == "/":
                self._advance()  # *
                self._advance()  # /
                return
            else:
                self._advance()

        # Si llegamos aquí, el comentario no fue cerrado
        raise LexerError(
            "Comentario de bloque sin cerrar (abierto con '/*')",
            start_line, start_col,
        )

    # ── Error ─────────────────────────────────────────────────────────────

    def _error(self, message: str) -> None:
        raise LexerError(message, self._line, self._column())
