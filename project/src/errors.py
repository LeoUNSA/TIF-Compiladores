"""Errores del analizador léxico y sintáctico."""


class LexerError(Exception):
    """Error detectado durante el análisis léxico."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.line   = line
        self.column = column

    def __str__(self) -> str:
        return f"[LexerError] Línea {self.line}, Col {self.column}: {self.args[0]}"


class ParseError(Exception):
    """Error detectado durante el análisis sintáctico."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.line   = line
        self.column = column

    def __str__(self) -> str:
        return f"[ParseError] Línea {self.line}, Col {self.column}: {self.args[0]}"


class SemanticError(Exception):
    """Error detectado durante el análisis semántico.

    A diferencia de las fases anteriores, el analizador semántico recolecta
    todos los errores en una lista en lugar de abortar en el primero: así el
    usuario (y la capa de IA) reciben un diagnóstico pedagógicamente completo.
    """

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.line   = line
        self.column = column

    def __str__(self) -> str:
        return f"[SemanticError] Línea {self.line}, Col {self.column}: {self.args[0]}"
