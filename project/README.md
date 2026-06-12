# SemanticC — Compilador MiniLang Aumentado con IA

**SemanticC** es una herramienta de línea de comandos que actúa como **asistente
semántico accesible para código fuente**. Compila programas del lenguaje **MiniLang**
a través de fases clásicas (léxico → sintáctico → semántico → CFG), expone las
representaciones internas del compilador como contexto estructurado y verificado, y
las entrega a un modelo de lenguaje (LLM) auto-hospedado que produce explicaciones en
lenguaje natural orientadas a desarrolladores con discapacidad visual.

> Idea central: **el compilador ya comprende formalmente el código; SemanticC hace que
> comunique esa comprensión de forma accesible.** Las respuestas de la IA no se generan
> desde texto fuente ambiguo, sino desde el AST tipado, la tabla de símbolos y el CFG.

Es el prototipo de la propuesta de investigación *"Compiladores Aumentados con IA para
Accesibilidad en Entornos de Programación"* (ver [`../propuesta.md`](../propuesta.md)).
No es una extensión de IDE, ni un lenguaje de propósito general, ni un compilador que
genere código máquina, ni un chatbot genérico.

---

## Arquitectura

```text
Código MiniLang (.ml)
    │
    ▼  src/lexer/        Analizador Léxico     → flujo de tokens
    ▼  src/parser/       Analizador Sintáctico → AST (patrón Visitor)
    ▼  src/semantic/     Analizador Semántico  → AST decorado con tipos + Tabla de Símbolos
    ▼  src/cfg/          Generador de CFG       → Grafo de Flujo de Control (uno por función)
    ▼  src/serialize/    Serializador           → documento JSON (las 3 fuentes de verdad)
    ▼  src/ai/           Capa de IA (Ollama)    → explicación accesible en lenguaje natural
```

Cada fase es un `Visitor` del AST, de modo que añadir un análisis nuevo no requiere
tocar los nodos. Las primeras cinco fases (el núcleo del compilador) **no tienen
dependencias externas**: solo la biblioteca estándar de Python. La capa de IA usa
únicamente `urllib` para hablar con un servidor Ollama local.

---

## Instalación

Requiere **Python 3.11+**.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # solo pytest
```

Para las consultas en lenguaje natural se necesita además
[**Ollama**](https://ollama.com) corriendo localmente con un modelo descargado:

```bash
ollama serve            # servidor en http://localhost:11434
ollama pull llama3.2:3b # modelo por defecto (~2 GB)
```

---

## Uso

### Inspección del compilador (sin IA, sin red)

```bash
# AST + análisis semántico (verificación de tipos y alcances)
.venv/bin/python main.py samples/factorial.ml

# Solo el flujo de tokens
.venv/bin/python main.py --tokens samples/hello.ml

# Tabla de símbolos del ámbito global
.venv/bin/python main.py --symbols samples/factorial.ml

# Grafo de Flujo de Control (un CFG por función)
.venv/bin/python main.py --cfg samples/control_flow.ml

# Documento semántico completo en JSON (el contexto que consume la IA)
.venv/bin/python main.py --json samples/factorial.ml
```

Los errores semánticos se reportan **todos a la vez** con posición exacta
`línea:columna` (ver `samples/type_error.ml` para un ejemplo deliberadamente erróneo).

### Consultas en lenguaje natural (requieren Ollama)

```bash
# Explicar qué hace una función
.venv/bin/python main.py --explain-function factorial samples/factorial.ml

# Describir una variable en su contexto (tipo, ámbito, inicializador)
.venv/bin/python main.py --describe resultado samples/factorial.ml

# Explicar los errores del compilador en lenguaje accesible
.venv/bin/python main.py --explain-error samples/type_error.ml

# Describir la estructura general del programa (navegación)
.venv/bin/python main.py --navigate samples/factorial.ml
```

Modelo alternativo: `--model qwen2.5:7b` o `export MINILANG_MODEL=...`.
Host alternativo: `export OLLAMA_HOST=http://otra-maquina:11434`.

### Tests

```bash
.venv/bin/python -m pytest tests/ -v          # 146 tests
.venv/bin/python -m pytest tests/test_cfg.py  # una suite
```

Los tests de la capa de IA usan un cliente falso: **no necesitan Ollama ni red**.

---

## El lenguaje MiniLang

Lenguaje imperativo de tipado estático, diseñado desde cero como sustrato controlado
para la investigación (no es el producto en sí).

```c
func int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

func void main() {
    int numero = 10;
    int resultado = factorial(numero);
    print("factorial de ", numero, " es: ", resultado);
}
```

- Tipos: `int`, `float`, `bool`, `string`, `void`.
- Funciones, variables tipadas, `if/else`, `while`, `for`, `break`, `continue`.
- E/S integrada: `print(...)`, `read(...)`.
- Operadores aritméticos, relacionales y lógicos con precedencia completa.
- Comentarios de línea (`//`) y de bloque (`/* */`).
- Verificación de tipos **estricta**: no hay coerción implícita `int`↔`float`.

---

## Estructura del proyecto

```text
project/
├── main.py              # CLI: orquesta las fases y las consultas
├── requirements.txt     # solo pytest
├── samples/             # programas de ejemplo (.ml), incl. uno con errores
├── src/
│   ├── errors.py        # LexerError, ParseError, SemanticError (con posición)
│   ├── lexer/           # tokens + Lexer
│   ├── parser/          # AST (Visitor) + Parser de descenso recursivo + ASTPrinter
│   ├── semantic/        # tabla de símbolos + analizador semántico
│   ├── cfg/             # bloques básicos + constructor del CFG
│   ├── serialize/       # AST+símbolos+CFG+diagnósticos → JSON
│   └── ai/              # cliente Ollama + selección de contexto + prompts + orquestador
└── tests/               # 146 tests (lexer, parser, semantic, cfg, serialize, ai)
```

Para el detalle de implementación y el estado por componente, ver
[`STATUS.md`](STATUS.md).

---

## Estado

Flujo completo funcionando de extremo a extremo. Progreso de la propuesta ≈ **90 %**:
implementadas todas las fases del compilador, la serialización y la integración con el
LLM. Pendiente: ajuste de calidad de respuestas, navegación interactiva accesible y la
evaluación empírica con usuarios. Ver [`STATUS.md`](STATUS.md) para el desglose.
