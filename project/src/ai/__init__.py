"""
Capa de Interpretación basada en IA del Compilador Aumentado.

Convierte el documento semántico del compilador (AST decorado, tabla de símbolos,
CFG, diagnósticos) en explicaciones accesibles en lenguaje natural, usando un LLM
auto-hospedado vía Ollama.

El núcleo del compilador (lexer/parser/semantic/cfg/serialize) sigue SIN dependencias
externas: esta capa usa solo `urllib` de la stdlib y se importa de forma perezosa.
"""

from .client import OllamaClient, OllamaError
from .assistant import Assistant

__all__ = ["OllamaClient", "OllamaError", "Assistant"]
