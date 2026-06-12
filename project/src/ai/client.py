"""
Cliente HTTP mínimo para Ollama (LLM auto-hospedado).

Usa solo la stdlib (`urllib`) para no introducir dependencias en el proyecto.
Apunta al servidor local de Ollama (por defecto http://localhost:11434).

Configuración por variables de entorno:
  - OLLAMA_HOST     (default: http://localhost:11434)
  - MINILANG_MODEL  (default: llama3.2:3b)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

DEFAULT_HOST  = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("MINILANG_MODEL", "llama3.2:3b")


class OllamaError(RuntimeError):
    """Error al contactar o usar el servidor de Ollama."""


class OllamaClient:
    """Cliente para el endpoint /api/generate de Ollama (no streaming)."""

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST,
                 timeout: int = 180, temperature: float = 0.2) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.temperature = temperature

    # ── Salud del servidor ────────────────────────────────────────────────

    def available(self) -> bool:
        """True si el servidor responde en /api/tags."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5):
                return True
        except (urllib.error.URLError, OSError):
            return False

    def has_model(self) -> bool:
        """True si `self.model` está descargado en el servidor."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5) as r:
                tags = json.loads(r.read())
        except (urllib.error.URLError, OSError, ValueError):
            return False
        names = {m.get("name", "") for m in tags.get("models", [])}
        # Ollama lista "llama3.2:3b"; acepta también sin tag explícito.
        return self.model in names or any(
            n.split(":")[0] == self.model.split(":")[0] for n in names)

    # ── Generación ────────────────────────────────────────────────────────

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Envía `prompt` al modelo y devuelve la respuesta como texto."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if system:
            payload["system"] = system
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise OllamaError(f"Ollama respondió {e.code}: {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            raise OllamaError(
                f"No se pudo contactar Ollama en {self.host}: {e}") from e
        return (body.get("response") or "").strip()
