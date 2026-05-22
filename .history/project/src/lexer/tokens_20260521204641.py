"""
Definición de tokens para MiniLang.

MiniLang es un lenguaje imperativo simple diseñado como sustrato del
Compilador Aumentado con IA para accesibilidad.
"""

from enum import Enum, auto


class TokenType(Enum):
    # ── Literales ──────────────────────────────────────────────────────────
    INTEGER     = auto()   # 42
    FLOAT       = auto()   # 3.14
    STRING      = auto()   # "hola"
    BOOL        = auto()   # true | false

    # ── Identificador ──────────────────────────────────────────────────────
    IDENTIFIER  = auto()   # nombre de variable / función

    # ── Palabras reservadas ────────────────────────────────────────────────
    KW_INT      = auto()   # int
    KW_FLOAT    = auto()   # float
    KW_BOOL     = auto()   # bool
    KW_STRING   = auto()   # string
    KW_VOID     = auto()   # void
    KW_FUNC     = auto()   # func
    KW_RETURN   = auto()   # return
    KW_IF       = auto()   # if
    KW_ELSE     = auto()   # else
    KW_WHILE    = auto()   # while
    KW_FOR      = auto()   # for
    KW_BREAK    = auto()   # break
    KW_CONTINUE = auto()   # continue
    KW_PRINT    = auto()   # print
    KW_READ     = auto()   # read
    KW_NULL     = auto()   # null

    # ── Operadores aritméticos ─────────────────────────────────────────────
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    STAR        = auto()   # *
    SLASH       = auto()   # /
    PERCENT     = auto()   # %

    # ── Operadores relacionales ────────────────────────────────────────────
    EQ_EQ       = auto()   # ==
    BANG_EQ     = auto()   # !=
    LESS        = auto()   # <
    LESS_EQ     = auto()   # <=
    GREATER     = auto()   # >
    GREATER_EQ  = auto()   # >=

    # ── Operadores lógicos ────────────────────────────────────────────────
    AMP_AMP     = auto()   # &&
    PIPE_PIPE   = auto()   # ||
    BANG        = auto()   # !

    # ── Asignación ───────────────────────────────────────────────────────
    EQ          = auto()   # =
    PLUS_EQ     = auto()   # +=
    MINUS_EQ    = auto()   # -=
    STAR_EQ     = auto()   # *=
    SLASH_EQ    = auto()   # /=

    # ── Delimitadores ────────────────────────────────────────────────────
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LBRACE      = auto()   # {
    RBRACE      = auto()   # }
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    SEMICOLON   = auto()   # ;
    COMMA       = auto()   # ,
    DOT         = auto()   # .

    # ── Fin de archivo ───────────────────────────────────────────────────
    EOF         = auto()


# Mapa: texto fuente → TokenType  (para palabras reservadas)
KEYWORDS: dict[str, TokenType] = {
    "int":      TokenType.KW_INT,
    "float":    TokenType.KW_FLOAT,
    "bool":     TokenType.KW_BOOL,
    "string":   TokenType.KW_STRING,
    "void":     TokenType.KW_VOID,
    "func":     TokenType.KW_FUNC,
    "return":   TokenType.KW_RETURN,
    "if":       TokenType.KW_IF,
    "else":     TokenType.KW_ELSE,
    "while":    TokenType.KW_WHILE,
    "for":      TokenType.KW_FOR,
    "break":    TokenType.KW_BREAK,
    "continue": TokenType.KW_CONTINUE,
    "print":    TokenType.KW_PRINT,
    "read":     TokenType.KW_READ,
    "true":     TokenType.BOOL,
    "false":    TokenType.BOOL,
    "null":     TokenType.KW_NULL,
}

# Tipos de datos válidos como palabras clave
TYPE_KEYWORDS: set[TokenType] = {
    TokenType.KW_INT,
    TokenType.KW_FLOAT,
    TokenType.KW_BOOL,
    TokenType.KW_STRING,
    TokenType.KW_VOID,
}


class Token:
    """Unidad léxica producida por el analizador léxico."""

    __slots__ = ("type", "lexeme", "literal", "line", "column")

    def __init__(
        self,
        type: TokenType,
        lexeme: str,
        literal: object,
        line: int,
        column: int,
    ) -> None:
        self.type    = type
        self.lexeme  = lexeme    # texto exacto en la fuente
        self.literal = literal   # valor Python ya evaluado (int, float, str, bool)
        self.line    = line
        self.column  = column

    # ── Representación ───────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"Token({self.type.name}, {self.lexeme!r}, "
            f"lit={self.literal!r}, {self.line}:{self.column})"
        )

    def __str__(self) -> str:
        return self.__repr__()
