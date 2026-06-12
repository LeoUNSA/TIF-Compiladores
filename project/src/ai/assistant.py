"""
Orquestador de la capa de IA.

`Assistant` combina la selección de contexto (`context`) con las plantillas de
prompt (`prompts`) y delega la generación en un cliente LLM. El cliente se inyecta
en el constructor (cualquier objeto con `.generate(prompt, system) -> str`), lo que
permite probar el orquestador sin red usando un cliente falso.
"""

from __future__ import annotations

from . import context, prompts


class Assistant:
    """Genera explicaciones accesibles a partir del documento semántico."""

    def __init__(self, client) -> None:
        self.client = client

    def explain_function(self, doc: dict, name: str) -> str:
        fn = context.find_function(doc, name)
        if fn is None:
            available = ", ".join(f["name"] for f in doc["functions"]) or "(ninguna)"
            raise ValueError(
                f"No existe la función '{name}'. Funciones disponibles: {available}")
        return self.client.generate(prompts.explain_function(fn), system=prompts.SYSTEM)

    def describe(self, doc: dict, name: str) -> str:
        hits = context.find_variable(doc, name)
        return self.client.generate(
            prompts.describe_variable(name, hits), system=prompts.SYSTEM)

    def navigate(self, doc: dict) -> str:
        struct = context.structure(doc)
        return self.client.generate(prompts.navigate(struct), system=prompts.SYSTEM)

    def explain_error(self, doc: dict, source: str) -> str:
        diag_ctx = context.diagnostics_with_source(doc, source)
        return self.client.generate(
            prompts.explain_error(diag_ctx), system=prompts.SYSTEM)
