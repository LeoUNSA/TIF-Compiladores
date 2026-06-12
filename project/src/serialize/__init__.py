"""Serialización de las representaciones del compilador a JSON para la capa de IA."""

from .json_serializer import JsonSerializer
from .document import serialize_program

__all__ = ["JsonSerializer", "serialize_program"]
