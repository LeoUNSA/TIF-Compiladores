"""Análisis semántico de MiniLang: tabla de símbolos y verificación de tipos."""

from .symbols import Symbol, Scope, SymbolTable
from .analyzer import SemanticAnalyzer

__all__ = ["Symbol", "Scope", "SymbolTable", "SemanticAnalyzer"]
