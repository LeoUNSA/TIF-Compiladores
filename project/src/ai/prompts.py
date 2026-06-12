"""
Plantillas de prompt para la capa de IA.

El prompt de sistema ANCLA al modelo a las representaciones formales del compilador:
debe explicar SOLO lo que está en los datos estructurados, sin inventar. Es la
diferencia central de SemanticC frente a un LLM ordinario que lee texto crudo.
"""

from __future__ import annotations

import json

SYSTEM = (
    "Eres SemanticC, un asistente que explica programas en lenguaje natural para "
    "personas con discapacidad visual. Recibes representaciones FORMALES y "
    "verificadas por un compilador (AST con tipos, tabla de símbolos, grafo de "
    "flujo de control y diagnósticos), NO el código fuente crudo.\n"
    "Reglas:\n"
    "1. Responde SOLO con base en los datos proporcionados; no inventes ni "
    "supongas nada que no esté en ellos.\n"
    "2. Escribe en español, claro y conciso.\n"
    "3. No uses tablas ni arte ASCII; usa frases y listas simples, aptas para "
    "lector de pantalla.\n"
    "4. Si los datos no alcanzan para responder, dilo explícitamente."
)


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def explain_function(fn: dict) -> str:
    return (
        f"Explica en lenguaje natural qué hace la función '{fn['name']}'. "
        "Describe su propósito, sus parámetros y su flujo de control "
        "(condicionales, bucles, retornos) usando la firma, las variables "
        "locales y el CFG.\n\n"
        f"Datos del compilador (JSON):\n{_json(fn)}"
    )


def describe_variable(name: str, hits: list) -> str:
    if not hits:
        return (
            f"No hay ninguna variable, parámetro ni global llamada '{name}' en los "
            "datos del compilador. Indícalo claramente."
        )
    return (
        f"Describe la variable '{name}' en su contexto: su tipo, dónde se declara "
        "(función y ámbito), y con qué valor se inicializa si la información está "
        "disponible.\n\n"
        f"Apariciones (JSON):\n{_json(hits)}"
    )


def navigate(struct: dict) -> str:
    return (
        "Describe la estructura general del programa para alguien que navega el "
        "código con lector de pantalla: cuántas funciones hay, qué hace cada una a "
        "grandes rasgos (tipo de retorno, parámetros, variables, bucles y ramas).\n\n"
        f"Resumen estructural (JSON):\n{_json(struct)}"
    )


def explain_error(diag_ctx: dict) -> str:
    if not diag_ctx["diagnosticos"]:
        return (
            "El compilador no reportó errores semánticos. Confírmalo de forma "
            "clara y breve."
        )
    return (
        "Explica los siguientes errores del compilador en lenguaje accesible. "
        "Para cada uno indica la línea, qué está mal y cómo corregirlo, en términos "
        "comprensibles. No inventes errores que no estén en la lista.\n\n"
        f"Diagnósticos y código referenciado (JSON):\n{_json(diag_ctx)}"
    )
