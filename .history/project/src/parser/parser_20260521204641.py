"""
Analizador Sintáctico (Parser) para MiniLang — Descenso Recursivo Predictivo.

Gramática (notación EBNF):

  program       → declaration* EOF

  declaration   → func_decl
                | var_decl
                | statement

  func_decl     → "func" type IDENTIFIER "(" params? ")" block
  params        → param ("," param)*
  param         → type IDENTIFIER

  var_decl      → type IDENTIFIER ("=" expression)? ";"
  type          → "int" | "float" | "bool" | "string" | "void"

  statement     → block
                | if_stmt
                | while_stmt
                | for_stmt
                | return_stmt
                | break_stmt
                | continue_stmt
                | print_stmt
                | read_stmt
                | expr_stmt

  block         → "{" declaration* "}"

  if_stmt       → "if" "(" expression ")" block
                  ("else" (if_stmt | block))?

  while_stmt    → "while" "(" expression ")" block

  for_stmt      → "for" "(" for_init expression? ";" expression? ")" block
  for_init      → var_decl | expr_stmt | ";"

  return_stmt   → "return" expression? ";"
  break_stmt    → "break" ";"
  continue_stmt → "continue" ";"
  print_stmt    → "print" "(" expression ("," expression)* ")" ";"
  read_stmt     → "read"  "(" IDENTIFIER ("," IDENTIFIER)* ")" ";"
  expr_stmt     → expression ";"

  expression    → assignment
  assignment    → IDENTIFIER ("=" | "+=" | "-=" | "*=" | "/=") assignment
                | logic_or
  logic_or      → logic_and ("||" logic_and)*
  logic_and     → equality ("&&" equality)*
  equality      → comparison (("==" | "!=") comparison)*
  comparison    → addition (("<" | "<=" | ">" | ">=") addition)*
  addition      → multiply (("+" | "-") multiply)*
  multiply      → unary (("*" | "/" | "%") unary)*
  unary         → ("!" | "-") unary | primary
  primary       → INTEGER | FLOAT | STRING | BOOL | "null"
                | IDENTIFIER ("(" arguments? ")")?
                | "(" expression ")"
  arguments     → expression ("," expression)*
"""

from __future__ import annotations

from typing import List, Optional

from ..errors import ParseError
from ..lexer.tokens import Token, TokenType, TYPE_KEYWORDS
from .ast_nodes import (
    # Statements
    AssignExpr, BinaryOp, Block, BoolLiteral, BreakStmt, CallExpr,
    ContinueStmt, ExprStmt, FloatLiteral, ForStmt, FunctionDecl,
    IdentifierExpr, IfStmt, IntLiteral, NullLiteral, Param,
    PrintStmt, Program, ReadStmt, ReturnStmt, StringLiteral,
    UnaryOp, VarDecl, WhileStmt,
    # Types
    Expression, Statement,
)

# Operadores de asignación compuesta
_ASSIGN_OPS = {
    TokenType.EQ,
    TokenType.PLUS_EQ,
    TokenType.MINUS_EQ,
    TokenType.STAR_EQ,
    TokenType.SLASH_EQ,
}


class Parser:
    """Parser de descenso recursivo predictivo para MiniLang."""

    def __init__(self, tokens: List[Token]) -> None:
        self._tokens:  List[Token] = tokens
        self._current: int         = 0

    # ── API pública ───────────────────────────────────────────────────────

    def parse(self) -> Program:
        """Analiza el flujo de tokens y devuelve el nodo raíz Program."""
        body: List[Statement] = []
        while not self._at_end():
            body.append(self._declaration())
        tok = self._peek()
        return Program(body=body, line=1, column=1)

    # ── Lectura de tokens ─────────────────────────────────────────────────

    def _at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _advance(self) -> Token:
        if not self._at_end():
            self._current += 1
        return self._previous()

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _consume(self, type: TokenType, message: str) -> Token:
        if self._check(type):
            return self._advance()
        tok = self._peek()
        raise ParseError(message, tok.line, tok.column)

    def _error(self, message: str) -> ParseError:
        tok = self._peek()
        return ParseError(message, tok.line, tok.column)

    # ── is_type_keyword ───────────────────────────────────────────────────

    def _is_type_kw(self) -> bool:
        return self._peek().type in TYPE_KEYWORDS

    def _consume_type(self) -> str:
        if not self._is_type_kw():
            tok = self._peek()
            raise ParseError(
                f"Se esperaba un tipo (int, float, bool, string, void), "
                f"se encontró '{tok.lexeme}'",
                tok.line, tok.column,
            )
        return self._advance().lexeme

    # ─────────────────────────────────────────────────────────────────────
    # Declaraciones
    # ─────────────────────────────────────────────────────────────────────

    def _declaration(self) -> Statement:
        if self._check(TokenType.KW_FUNC):
            return self._func_decl()
        if self._is_type_kw():
            return self._var_decl()
        return self._statement()

    # ── Función ───────────────────────────────────────────────────────────

    def _func_decl(self) -> FunctionDecl:
        kw = self._consume(TokenType.KW_FUNC, "Se esperaba 'func'")
        return_type = self._consume_type()
        name_tok = self._consume(
            TokenType.IDENTIFIER,
            "Se esperaba el nombre de la función",
        )
        self._consume(TokenType.LPAREN, "Se esperaba '(' después del nombre")

        params: List[Param] = []
        if not self._check(TokenType.RPAREN):
            params = self._params()

        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar parámetros")
        body = self._block()

        return FunctionDecl(
            name=name_tok.lexeme,
            return_type=return_type,
            params=params,
            body=body,
            line=kw.line,
            column=kw.column,
        )

    def _params(self) -> List[Param]:
        params: List[Param] = []
        while True:
            type_name = self._consume_type()
            name_tok  = self._consume(
                TokenType.IDENTIFIER,
                "Se esperaba el nombre del parámetro",
            )
            params.append(
                Param(
                    type_name=type_name,
                    name=name_tok.lexeme,
                    line=name_tok.line,
                    column=name_tok.column,
                )
            )
            if not self._match(TokenType.COMMA):
                break
        return params

    # ── Declaración de variable ───────────────────────────────────────────

    def _var_decl(self) -> VarDecl:
        type_tok  = self._advance()          # ya sabemos que es tipo
        name_tok  = self._consume(
            TokenType.IDENTIFIER,
            f"Se esperaba el nombre de la variable después de '{type_tok.lexeme}'",
        )
        initializer: Optional[Expression] = None
        if self._match(TokenType.EQ):
            initializer = self._expression()

        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final de la declaración")
        return VarDecl(
            type_name=type_tok.lexeme,
            name=name_tok.lexeme,
            initializer=initializer,
            line=type_tok.line,
            column=type_tok.column,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Sentencias
    # ─────────────────────────────────────────────────────────────────────

    def _statement(self) -> Statement:
        if self._check(TokenType.LBRACE):
            return self._block()
        if self._check(TokenType.KW_IF):
            return self._if_stmt()
        if self._check(TokenType.KW_WHILE):
            return self._while_stmt()
        if self._check(TokenType.KW_FOR):
            return self._for_stmt()
        if self._check(TokenType.KW_RETURN):
            return self._return_stmt()
        if self._check(TokenType.KW_BREAK):
            tok = self._advance()
            self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de 'break'")
            return BreakStmt(line=tok.line, column=tok.column)
        if self._check(TokenType.KW_CONTINUE):
            tok = self._advance()
            self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de 'continue'")
            return ContinueStmt(line=tok.line, column=tok.column)
        if self._check(TokenType.KW_PRINT):
            return self._print_stmt()
        if self._check(TokenType.KW_READ):
            return self._read_stmt()
        return self._expr_stmt()

    def _block(self) -> Block:
        brace = self._consume(TokenType.LBRACE, "Se esperaba '{'")
        body: List[Statement] = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            body.append(self._declaration())
        self._consume(TokenType.RBRACE, "Se esperaba '}' al cerrar el bloque")
        return Block(body=body, line=brace.line, column=brace.column)

    def _if_stmt(self) -> IfStmt:
        kw = self._consume(TokenType.KW_IF, "Se esperaba 'if'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'if'")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar condición")
        then_branch = self._block()

        else_branch: Optional[Statement] = None
        if self._match(TokenType.KW_ELSE):
            if self._check(TokenType.KW_IF):
                else_branch = self._if_stmt()
            else:
                else_branch = self._block()

        return IfStmt(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=kw.line,
            column=kw.column,
        )

    def _while_stmt(self) -> WhileStmt:
        kw = self._consume(TokenType.KW_WHILE, "Se esperaba 'while'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'while'")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar condición")
        body = self._block()
        return WhileStmt(condition=condition, body=body, line=kw.line, column=kw.column)

    def _for_stmt(self) -> ForStmt:
        kw = self._consume(TokenType.KW_FOR, "Se esperaba 'for'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'for'")

        # Inicialización
        init: Optional[Statement] = None
        if self._check(TokenType.SEMICOLON):
            self._advance()
        elif self._is_type_kw():
            init = self._var_decl()  # incluye el ;
        else:
            init = self._expr_stmt()

        # Condición
        condition: Optional[Expression] = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' en for (después de condición)")

        # Actualización
        update: Optional[Expression] = None
        if not self._check(TokenType.RPAREN):
            update = self._expression()
        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar for")

        body = self._block()
        return ForStmt(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=kw.line,
            column=kw.column,
        )

    def _return_stmt(self) -> ReturnStmt:
        kw = self._consume(TokenType.KW_RETURN, "Se esperaba 'return'")
        value: Optional[Expression] = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de 'return'")
        return ReturnStmt(value=value, line=kw.line, column=kw.column)

    def _print_stmt(self) -> PrintStmt:
        kw = self._consume(TokenType.KW_PRINT, "Se esperaba 'print'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'print'")
        args: List[Expression] = []
        if not self._check(TokenType.RPAREN):
            args.append(self._expression())
            while self._match(TokenType.COMMA):
                args.append(self._expression())
        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar print")
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de print")
        return PrintStmt(args=args, line=kw.line, column=kw.column)

    def _read_stmt(self) -> ReadStmt:
        kw = self._consume(TokenType.KW_READ, "Se esperaba 'read'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'read'")
        targets: List[str] = []
        tok = self._consume(TokenType.IDENTIFIER, "Se esperaba una variable en read")
        targets.append(tok.lexeme)
        while self._match(TokenType.COMMA):
            tok = self._consume(TokenType.IDENTIFIER, "Se esperaba una variable")
            targets.append(tok.lexeme)
        self._consume(TokenType.RPAREN, "Se esperaba ')' al cerrar read")
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' después de read")
        return ReadStmt(targets=targets, line=kw.line, column=kw.column)

    def _expr_stmt(self) -> ExprStmt:
        expr = self._expression()
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final de la expresión")
        return ExprStmt(expr=expr, line=expr.line, column=expr.column)

    # ─────────────────────────────────────────────────────────────────────
    # Expresiones
    # ─────────────────────────────────────────────────────────────────────

    def _expression(self) -> Expression:
        return self._assignment()

    def _assignment(self) -> Expression:
        """assignment → IDENTIFIER (<op_asig>) assignment | logic_or"""
        # Lookahead: si es IDENTIFIER seguido de operador de asignación
        if (
            self._check(TokenType.IDENTIFIER)
            and self._current + 1 < len(self._tokens)
            and self._tokens[self._current + 1].type in _ASSIGN_OPS
        ):
            name_tok = self._advance()
            op_tok   = self._advance()
            value    = self._assignment()
            return AssignExpr(
                name=name_tok.lexeme,
                operator=op_tok.lexeme,
                value=value,
                line=name_tok.line,
                column=name_tok.column,
            )
        return self._logic_or()

    def _logic_or(self) -> Expression:
        left = self._logic_and()
        while self._match(TokenType.PIPE_PIPE):
            op    = self._previous()
            right = self._logic_and()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _logic_and(self) -> Expression:
        left = self._equality()
        while self._match(TokenType.AMP_AMP):
            op    = self._previous()
            right = self._equality()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _equality(self) -> Expression:
        left = self._comparison()
        while self._match(TokenType.EQ_EQ, TokenType.BANG_EQ):
            op    = self._previous()
            right = self._comparison()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _comparison(self) -> Expression:
        left = self._addition()
        while self._match(
            TokenType.LESS, TokenType.LESS_EQ,
            TokenType.GREATER, TokenType.GREATER_EQ,
        ):
            op    = self._previous()
            right = self._addition()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _addition(self) -> Expression:
        left = self._multiply()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op    = self._previous()
            right = self._multiply()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _multiply(self) -> Expression:
        left = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op    = self._previous()
            right = self._unary()
            left  = BinaryOp(left=left, operator=op.lexeme, right=right,
                             line=op.line, column=op.column)
        return left

    def _unary(self) -> Expression:
        if self._match(TokenType.BANG, TokenType.MINUS):
            op      = self._previous()
            operand = self._unary()
            return UnaryOp(operator=op.lexeme, operand=operand,
                           line=op.line, column=op.column)
        return self._primary()

    def _primary(self) -> Expression:
        tok = self._peek()

        if self._match(TokenType.INTEGER):
            return IntLiteral(value=self._previous().literal,
                              line=tok.line, column=tok.column)

        if self._match(TokenType.FLOAT):
            return FloatLiteral(value=self._previous().literal,
                                line=tok.line, column=tok.column)

        if self._match(TokenType.STRING):
            return StringLiteral(value=self._previous().literal,
                                 line=tok.line, column=tok.column)

        if self._match(TokenType.BOOL):
            return BoolLiteral(value=self._previous().literal,
                               line=tok.line, column=tok.column)

        if self._match(TokenType.KW_NULL):
            return NullLiteral(line=tok.line, column=tok.column)

        if self._match(TokenType.IDENTIFIER):
            name = self._previous()
            # ¿llamada a función?
            if self._match(TokenType.LPAREN):
                args: List[Expression] = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._expression())
                self._consume(TokenType.RPAREN,
                              f"Se esperaba ')' al cerrar la llamada a '{name.lexeme}'")
                return CallExpr(name=name.lexeme, arguments=args,
                                line=name.line, column=name.column)
            return IdentifierExpr(name=name.lexeme,
                                  line=name.line, column=name.column)

        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN,
                          "Se esperaba ')' al cerrar la expresión agrupada")
            return expr

        raise self._error(
            f"Se esperaba una expresión, se encontró '{tok.lexeme}'"
        )
