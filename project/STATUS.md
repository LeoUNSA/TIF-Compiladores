# Estado de Implementación — SemanticC / MiniLang Compiler

## ¿Qué es el producto?

**SemanticC** es una herramienta de línea de comandos (CLI) que actúa como **asistente semántico accesible para código fuente**. No es:
- una extensión de IDE
- un lenguaje de programación de propósito general
- un compilador en el sentido tradicional (no produce código ejecutable)
- un chatbot genérico de IA

Es una herramienta que:
1. toma un archivo de código fuente MiniLang,
2. lo procesa a través de un compilador propio (léxico → sintáctico → semántico → CFG),
3. expone las representaciones internas resultantes como contexto estructurado a un LLM,
4. devuelve al usuario respuestas en lenguaje natural, **ancladas en la semántica formal del programa**.

### Consultas que responderá

```bash
python main.py --explain-function factorial archivo.ml
# "La función `factorial` recibe un entero `n`. Si `n` es menor o igual a 1,
#  retorna 1 (caso base). En caso contrario, retorna `n` * factorial(n-1)."

python main.py --describe resultado archivo.ml
# "`resultado` es una variable entera en `main`, inicializada con el valor
#  retornado por la llamada a factorial(numero)."

python main.py --explain-error archivo.ml
# "Línea 7: falta `;` al final de la declaración de `x`. En MiniLang toda
#  declaración de variable debe terminar con punto y coma."

python main.py --navigate archivo.ml
# "El programa tiene 2 funciones: factorial (int) y main (void).
#  `factorial` contiene 1 bloque con un if y un return."
```

La diferencia respecto a un LLM ordinario: las respuestas no se construyen desde texto fuente ambiguo, sino desde el AST, la tabla de símbolos y el CFG — representaciones verificadas por el compilador.

---

## Por qué MiniLang y no Python/C/Rust

MiniLang es el **lenguaje de demostración/sustrato**, no el producto. Se diseñó desde cero para:
- controlar completamente las estructuras internas que se exponen al LLM,
- producir errores pedagógicamente ricos con posición exacta,
- demostrar que la arquitectura de SemanticC es agnóstica del lenguaje fuente.

En producción, el mismo diseño aplicaría sobre un frontend de Tree-sitter, LLVM o Python AST.

---


## Estructura del proyecto

```
project/
├── main.py                  ← CLI principal
├── requirements.txt         ← solo pytest
├── samples/
│   ├── hello.ml             ← programa mínimo
│   ├── factorial.ml         ← recursión + condicionales
│   └── control_flow.ml      ← while, for, break, continue
├── src/
│   ├── errors.py            ← LexerError, ParseError (con línea:columna)
│   ├── lexer/
│   │   ├── tokens.py        ← TokenType (68 tipos), Token, KEYWORDS
│   │   └── lexer.py         ← Lexer completo
│   ├── parser/
│   │   ├── ast_nodes.py     ← 20+ nodos AST + patrón Visitor
│   │   ├── parser.py        ← Parser recursivo descendente (gramática EBNF)
│   │   └── ast_printer.py   ← Pretty-printer del AST
│   ├── semantic/
│   │   ├── symbols.py       ← Symbol, Scope, SymbolTable (ámbitos anidados)
│   │   └── analyzer.py      ← SemanticAnalyzer (Visitor): tipos + scopes
│   ├── cfg/
│   │   ├── blocks.py        ← BasicBlock, ControlFlowGraph, format_cfg
│   │   └── builder.py       ← CFGBuilder (Visitor): un CFG por función
│   ├── serialize/
│   │   ├── json_serializer.py ← JsonSerializer (Visitor): AST → dict
│   │   └── document.py      ← serialize_program: AST+símbolos+CFG+diagnósticos
│   └── ai/                  ← capa de IA (Ollama, solo stdlib)
│       ├── client.py        ← OllamaClient (urllib, /api/generate)
│       ├── context.py       ← selección de contexto por consulta
│       ├── prompts.py       ← prompt de sistema + plantillas (español)
│       └── assistant.py     ← orquestador (cliente inyectable)
└── tests/
    ├── test_lexer.py        ← 31 tests
    ├── test_parser.py       ← 47 tests
    ├── test_semantic.py     ← 33 tests
    ├── test_cfg.py          ← 15 tests
    ├── test_serialize.py    ← 10 tests
    └── test_ai.py           ← 10 tests (sin red, cliente falso)
```

---

## Cómo ejecutar

```bash
# Crear entorno virtual (Arch Linux / cualquier distro)
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Analizar un programa y ver el AST
.venv/bin/python main.py samples/factorial.ml

# Ver solo el flujo de tokens
.venv/bin/python main.py --tokens samples/hello.ml

# Analizar + mostrar la tabla de símbolos del ámbito global
.venv/bin/python main.py --symbols samples/factorial.ml

# Ver un programa con errores semánticos (diagnóstico completo)
.venv/bin/python main.py samples/type_error.ml

# Mostrar el Grafo de Flujo de Control (un CFG por función)
.venv/bin/python main.py --cfg samples/control_flow.ml

# Emitir el documento semántico (JSON) que consume la capa de IA
.venv/bin/python main.py --json samples/factorial.ml

# ── Consultas en lenguaje natural (requieren Ollama) ──────────────────────────
# Requisitos: `ollama serve` corriendo y el modelo descargado:
#   ollama pull llama3.2:3b
.venv/bin/python main.py --navigate samples/factorial.ml
.venv/bin/python main.py --explain-function factorial samples/factorial.ml
.venv/bin/python main.py --describe resultado samples/factorial.ml
.venv/bin/python main.py --explain-error samples/type_error.ml
# Modelo alternativo: --model qwen2.5:7b  (o export MINILANG_MODEL=...)

# Correr tests
.venv/bin/python -m pytest tests/ -v
```

---

## Resumen de la implementación actual

### Analizador Léxico (`src/lexer/`)

- **68 tipos de token** organizados en: literales, palabras reservadas, operadores, delimitadores, EOF.
- Palabras reservadas: `int float bool string void func return if else while for break continue print read null true false`.
- Operadores compuestos: `==`, `!=`, `<=`, `>=`, `&&`, `||`, `+=`, `-=`, `*=`, `/=`.
- Literales de cadena con secuencias de escape: `\n`, `\t`, `\\`, `\"`.
- Comentarios de línea (`//`) y de bloque (`/* */`) con soporte multilinea.
- Reporte de errores con posición exacta `línea:columna`.

### Analizador Sintáctico (`src/parser/`)

- **Parser de descenso recursivo** basado en gramática EBNF completa.
- Soporta todos los constructos de MiniLang: funciones, variables, if/else, while, for, break, continue, print, read, expresiones con precedencia correcta.
- **Precedencia de operadores** (de menor a mayor): `||` → `&&` → `==`/`!=` → `<`/`<=`/`>`/`>=` → `+`/`-` → `*`/`/`/`%` → unario.
- **AST con patrón Visitor**: permite añadir recorridos (análisis semántico, CFG, serialización IA) sin tocar los nodos.
- **ASTPrinter**: genera representación indentada del AST, legible por humanos y procesable por la capa de IA.

### Analizador Semántico (`src/semantic/`)

- **Tabla de símbolos** (`symbols.py`): `Symbol` (var/param/func con tipo, posición y, para funciones, tipos de parámetros), `Scope` con enlace al padre y `SymbolTable` como pila de ámbitos anidados (global → función → bloque → for).
- **SemanticAnalyzer** (`analyzer.py`): tercer `Visitor` del AST. Verifica de forma **estricta** (sin coerción `int`↔`float`):
  - variables/funciones no declaradas y redeclaraciones en el mismo ámbito,
  - compatibilidad de tipos en inicializadores, asignaciones (`=` y compuestas), operadores aritméticos/relacionales/lógicos y unarios,
  - aridad y tipos de argumentos en llamadas; tipo de retorno frente a la firma,
  - condiciones `bool` en `if`/`while`/`for`,
  - `break`/`continue` solo dentro de bucles.
- **Pre-pase de firmas**: registra todas las funciones antes de analizar cuerpos ⇒ llamadas hacia adelante y recursión.
- **Recolección de todos los errores** (no aborta en el primero) con tipo "veneno" (`None`) para evitar cascadas. Decora cada `Expression` con `inferred_type` para el futuro CFG y la capa de IA.
- CLI: `--symbols` vuelca la tabla del ámbito global; los errores se imprimen a `stderr` con `línea:columna`.

### Grafo de Flujo de Control (`src/cfg/`)

- **Estructuras** (`blocks.py`): `BasicBlock` (secuencia de sentencias + aristas + condición de control opcional), `Edge` (arista etiquetada `true`/`false`/`break`/`continue`), `ControlFlowGraph` (bloques, `entry`/`exit` únicos). `format_cfg` produce una representación textual lineal y accesible.
- **CFGBuilder** (`builder.py`): cuarto `Visitor` del AST. Construye **un CFG por función**. Hila un "bloque actual" que se vuelve `None` tras `return`/`break`/`continue` (marca el código inalcanzable). Modela:
  - `if`/`else` con ramas `true`/`false` y bloque de convergencia (`if.end`); si ambas ramas terminan, no se crea convergencia,
  - `while` con bloque de condición, cuerpo y arista de retroceso,
  - `for` con bloque de condición, cuerpo, `for.update` (destino de `continue`) y salida,
  - `break` → salida del bucle, `continue` → cabecera (`while`) o `update` (`for`).
- Las expresiones se tratan de forma atómica (no se modela el cortocircuito de `&&`/`||`). CLI: `--cfg`.

### Serialización JSON (`src/serialize/`)

- **JsonSerializer** (`json_serializer.py`): quinto `Visitor`. Convierte cualquier nodo AST en un diccionario JSON-compatible; cada expresión incluye su `type` (= `inferred_type` del análisis semántico) ⇒ contexto verificado, no texto crudo.
- **serialize_program** (`document.py`): ensambla el "documento semántico" que consume el LLM, combinando las tres fuentes de verdad: `functions` (firma + `params` + `locals` con tipo/posición/scope + `ast` decorado + `cfg`), `globals`, y `diagnostics` (errores semánticos con posición).
- CLI: `--json` emite el documento **siempre** (con o sin errores; los diagnósticos van dentro), pensado para consultas tipo `--explain-error`.

### Capa de IA (`src/ai/`)

- **LLM auto-hospedado vía Ollama** (`client.py`): `OllamaClient` habla con `http://localhost:11434/api/generate` usando solo `urllib` (sin dependencias nuevas). Comprueba salud (`available()`) y presencia del modelo (`has_model()`). Configurable por `OLLAMA_HOST` / `MINILANG_MODEL`; modelo por defecto `llama3.2:3b`.
- **Selección de contexto** (`context.py`): por cada consulta extrae del documento JSON solo la porción relevante (función, variable + su inicializador, resumen estructural, o diagnósticos + líneas de fuente).
- **Prompts** (`prompts.py`): prompt de sistema que **ancla** al modelo a los datos formales del compilador (no inventar, español, salida apta para lector de pantalla).
- **Assistant** (`assistant.py`): orquestador con cliente **inyectable** (se prueba sin red). Consultas: `--explain-function`, `--describe`, `--explain-error`, `--navigate`.
- El núcleo del compilador sigue **sin dependencias externas**; la capa de IA se importa de forma perezosa solo cuando se usa una de esas flags.

### Tests

| Suite | Tests | Estado |
|---|---|---|
| `test_lexer.py` | 31 | ✅ todos pasan |
| `test_parser.py` | 47 | ✅ todos pasan |
| `test_semantic.py` | 33 | ✅ todos pasan |
| `test_cfg.py` | 15 | ✅ todos pasan |
| `test_serialize.py` | 10 | ✅ todos pasan |
| `test_ai.py` | 10 | ✅ todos pasan (sin red) |
| **Total** | **146** | ✅ |

---

## Estado respecto a la propuesta completa

| Componente | Estado | Notas |
|---|---|---|
| **Diseño del lenguaje MiniLang** | ✅ Completo | Tipos, operadores, constructos de control |
| **Analizador Léxico** | ✅ Completo | 68 tokens, errores con posición |
| **Analizador Sintáctico** | ✅ Completo | Descenso recursivo, gramática EBNF |
| **AST + Visitor** | ✅ Completo | 20+ nodos, ASTPrinter |
| **Analizador Semántico** | ✅ Completo | Tipos estrictos, scopes, retorno, flujo; recolecta todos los errores |
| **Tabla de Símbolos** | ✅ Completo | Symbol/Scope/SymbolTable, ámbitos anidados |
| **Generación de CFG** | ✅ Completo | Bloques básicos, aristas, un CFG por función |
| **Serialización para IA** | ✅ Completo | AST+símbolos+CFG+diagnósticos → JSON (`--json`) |
| **Integración LLM** | ✅ Completo | Ollama (llama3.2:3b); 4 consultas en lenguaje natural |
| **Interfaz accesible** | ◐ Parcial | Salida en texto plano para lector de pantalla; falta navegación interactiva |
| **Evaluación con usuarios** | ⏳ Pendiente | Estudio empírico con participantes |

### Progreso general de la propuesta: ~90%

El flujo completo de la propuesta funciona de extremo a extremo: código MiniLang → léxico → sintáctico → semántico → CFG → documento JSON → **LLM auto-hospedado (Ollama) → explicación accesible en lenguaje natural**. Las cuatro consultas (`--explain-function`, `--describe`, `--explain-error`, `--navigate`) responden ancladas en las representaciones verificadas del compilador.

---

## Próximos pasos sugeridos

1. **Calidad de respuestas** — `llama3.2:3b` a veces ignora datos (p. ej. ramas de un `if`) o sugiere sintaxis ajena a MiniLang. Evaluar un modelo mayor (`qwen2.5:7b`) y endurecer los prompts (few-shot con ejemplos de MiniLang).
2. **Interfaz accesible interactiva** — más allá del texto plano: navegación por funciones/bloques con teclado.
3. **Evaluación empírica** — estudio con desarrolladores con discapacidad visual: comprensión, navegación, depuración (NASA-TLX, tiempo, tasa de error).
4. **Errores léxicos/sintácticos en `--explain-error`** — hoy la capa de IA requiere un AST válido; extenderla para explicar también fallos de parseo.
