"""Tests del analizador léxico (Lexer) de MiniLang."""

import pytest
from src.lexer.lexer import Lexer
from src.lexer.tokens import TokenType
from src.errors import LexerError


# ── Helpers ───────────────────────────────────────────────────────────────────

def lex(source: str):
    """Retorna la lista de tokens sin el EOF."""
    tokens = Lexer(source).tokenize()
    return [t for t in tokens if t.type != TokenType.EOF]


def types(source: str):
    """Retorna solo los tipos de token (sin EOF)."""
    return [t.type for t in lex(source)]


# ── Literales ─────────────────────────────────────────────────────────────────

class TestLiterals:
    def test_integer(self):
        toks = lex("42")
        assert len(toks) == 1
        assert toks[0].type    == TokenType.INTEGER
        assert toks[0].literal == 42

    def test_float(self):
        toks = lex("3.14")
        assert len(toks) == 1
        assert toks[0].type    == TokenType.FLOAT
        assert abs(toks[0].literal - 3.14) < 1e-9

    def test_string_simple(self):
        toks = lex('"hola mundo"')
        assert toks[0].type    == TokenType.STRING
        assert toks[0].literal == "hola mundo"

    def test_string_escape_newline(self):
        toks = lex(r'"linea1\nlinea2"')
        assert toks[0].literal == "linea1\nlinea2"

    def test_string_escape_tab(self):
        toks = lex(r'"col1\tcol2"')
        assert toks[0].literal == "col1\tcol2"

    def test_string_escape_backslash(self):
        toks = lex(r'"a\\b"')
        assert toks[0].literal == "a\\b"

    def test_bool_true(self):
        toks = lex("true")
        assert toks[0].type    == TokenType.BOOL
        assert toks[0].literal is True

    def test_bool_false(self):
        toks = lex("false")
        assert toks[0].type    == TokenType.BOOL
        assert toks[0].literal is False


# ── Palabras reservadas ───────────────────────────────────────────────────────

class TestKeywords:
    def test_all_keywords(self):
        src = "int float bool string void func return if else while for break continue print read null"
        expected = [
            TokenType.KW_INT, TokenType.KW_FLOAT, TokenType.KW_BOOL,
            TokenType.KW_STRING, TokenType.KW_VOID, TokenType.KW_FUNC,
            TokenType.KW_RETURN, TokenType.KW_IF, TokenType.KW_ELSE,
            TokenType.KW_WHILE, TokenType.KW_FOR, TokenType.KW_BREAK,
            TokenType.KW_CONTINUE, TokenType.KW_PRINT, TokenType.KW_READ,
            TokenType.KW_NULL,
        ]
        assert types(src) == expected

    def test_identifier_not_keyword(self):
        toks = lex("integer")
        assert toks[0].type == TokenType.IDENTIFIER

    def test_identifier_with_underscore(self):
        toks = lex("mi_variable")
        assert toks[0].type    == TokenType.IDENTIFIER
        assert toks[0].lexeme  == "mi_variable"


# ── Operadores ────────────────────────────────────────────────────────────────

class TestOperators:
    def test_arithmetic(self):
        assert types("+ - * / %") == [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
            TokenType.SLASH, TokenType.PERCENT,
        ]

    def test_relational(self):
        assert types("== != < <= > >=") == [
            TokenType.EQ_EQ, TokenType.BANG_EQ, TokenType.LESS,
            TokenType.LESS_EQ, TokenType.GREATER, TokenType.GREATER_EQ,
        ]

    def test_logical(self):
        assert types("&& || !") == [
            TokenType.AMP_AMP, TokenType.PIPE_PIPE, TokenType.BANG,
        ]

    def test_compound_assignment(self):
        assert types("+= -= *= /=") == [
            TokenType.PLUS_EQ, TokenType.MINUS_EQ,
            TokenType.STAR_EQ, TokenType.SLASH_EQ,
        ]

    def test_assignment(self):
        assert types("=") == [TokenType.EQ]


# ── Delimitadores ─────────────────────────────────────────────────────────────

class TestDelimiters:
    def test_delimiters(self):
        assert types("( ) { } [ ] ; , .") == [
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.LBRACKET, TokenType.RBRACKET,
            TokenType.SEMICOLON, TokenType.COMMA, TokenType.DOT,
        ]


# ── Comentarios ───────────────────────────────────────────────────────────────

class TestComments:
    def test_line_comment_ignored(self):
        assert lex("// este comentario es ignorado\n42") == lex("42")

    def test_block_comment_ignored(self):
        assert lex("/* comentario */ 42") == lex("42")

    def test_block_comment_multiline(self):
        src = "/* línea 1\n   línea 2 */ 99"
        toks = lex(src)
        assert len(toks) == 1
        assert toks[0].literal == 99

    def test_unclosed_block_comment_raises(self):
        with pytest.raises(LexerError) as exc_info:
            Lexer("/* sin cerrar").tokenize()
        assert exc_info.value.line == 1


# ── Posición (línea:columna) ──────────────────────────────────────────────────

class TestPosition:
    def test_line_tracking(self):
        src = "42\n99"
        toks = lex(src)
        assert toks[0].line == 1
        assert toks[1].line == 2

    def test_column_tracking(self):
        toks = lex("   77")
        assert toks[0].column == 4

    def test_column_after_newline(self):
        src = "1\n  2"
        toks = lex(src)
        assert toks[1].column == 3


# ── Errores léxicos ───────────────────────────────────────────────────────────

class TestLexerErrors:
    def test_unexpected_char(self):
        with pytest.raises(LexerError):
            Lexer("@").tokenize()

    def test_unclosed_string(self):
        with pytest.raises(LexerError):
            Lexer('"sin cerrar').tokenize()

    def test_invalid_escape(self):
        with pytest.raises(LexerError):
            Lexer(r'"\q"').tokenize()

    def test_single_ampersand(self):
        with pytest.raises(LexerError):
            Lexer("&").tokenize()

    def test_single_pipe(self):
        with pytest.raises(LexerError):
            Lexer("|").tokenize()


# ── Programa completo ─────────────────────────────────────────────────────────

class TestFullProgram:
    def test_var_declaration(self):
        src = "int x = 42;"
        t = types(src)
        assert t == [
            TokenType.KW_INT, TokenType.IDENTIFIER,
            TokenType.EQ, TokenType.INTEGER, TokenType.SEMICOLON,
        ]

    def test_function_signature(self):
        src = "func int suma(int a, int b)"
        t = types(src)
        assert TokenType.KW_FUNC in t
        assert TokenType.KW_INT  in t
