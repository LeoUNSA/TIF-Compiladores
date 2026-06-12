# IMPLEMENTACIÓN — SemanticC / MiniLang

Documento técnico de implementación. Cubre **qué está hecho**, **qué falta** y las
**partes cruciales** del diseño (las decisiones que cruzan varios archivos y que hay
que entender antes de tocar el código).

Para uso de la CLI ver [`README.md`](README.md). Para el tablero de progreso por
componente ver [`STATUS.md`](STATUS.md). Este archivo explica el *cómo* y el *por qué*.

---

## 1. Qué está logrado

Pipeline completo de extremo a extremo, **146 tests en verde**, ≈90% de la propuesta:

```
código.ml → léxico → sintáctico → semántico → CFG → documento JSON → LLM (Ollama) → explicación accesible
```

| Fase | Paquete | Entrega | Estado |
|---|---|---|---|
| Léxico | `src/lexer/` | flujo de tokens (68 tipos) con `línea:columna` | ✅ |
| Sintáctico | `src/parser/` | AST (20+ nodos) vía descenso recursivo | ✅ |
| Semántico | `src/semantic/` | AST decorado con tipos + tabla de símbolos | ✅ |
| CFG | `src/cfg/` | un grafo de flujo por función | ✅ |
| Serialización | `src/serialize/` | documento JSON (las 3 fuentes de verdad) | ✅ |
| Capa IA | `src/ai/` | 4 consultas en lenguaje natural vía Ollama | ✅ |

Las 4 consultas funcionan en vivo y ancladas en datos verificados:
`--explain-function`, `--describe`, `--explain-error`, `--navigate`.

El núcleo del compilador (fases 1–5) es **stdlib puro**. La capa de IA usa solo
`urllib` y se importa de forma perezosa, así que el núcleo se prueba sin red ni modelo.

---

## 2. Qué falta

| Pendiente | Por qué importa | Bloqueante de |
|---|---|---|
| **Fidelidad de respuesta** | `llama3.2:3b` a veces ignora el contexto verificado (afirma que `factorial` no tiene `if` aunque el JSON dice `ramas_if:1`) o emite sintaxis ajena a MiniLang. La arquitectura entrega contexto correcto; el modelo pequeño lo desperdicia al generar. | Tesis central del paper |
| **Evaluación empírica** | Sin estudio con usuarios (NASA-TLX, tiempo, tasa de error). Es la *contribución empírica* de la propuesta. | Contribución empírica |
| **`--explain-error` sólo semántico** | Requiere un AST válido; errores léxicos/sintácticos no llegan a la capa de IA (sin parse no hay documento JSON). | Cobertura completa de diagnósticos |
| **Navegación accesible interactiva** | Hoy `--navigate` *describe* la estructura; no permite *recorrerla* (estilo CodeTalk, por teclado bloque a bloque). | Contribución de accesibilidad |
| **Cortocircuito en CFG** | `&&`/`||` se tratan como expresiones atómicas; el CFG no modela su evaluación perezosa. Aceptable para el prototipo, impreciso para análisis de flujo fino. | Precisión del CFG |

Resumen: contribuciones **conceptual** y **técnica** demostradas; la **empírica** no
empezada (esperable en etapa de prototipo).

---

## 3. Partes cruciales de la implementación

Estas son las decisiones que hay que entender **antes** de extender el compilador.
No son detalles locales: cada una atraviesa varios archivos.

### 3.1 El patrón Visitor es portante

`src/parser/ast_nodes.py` define `Node → Statement | Expression` y la interfaz abstracta
`Visitor`. **Cada fase del compilador es una subclase de `Visitor`** sobre el mismo AST:

| Visitor | Archivo | Rol |
|---|---|---|
| `ASTPrinter` | `parser/ast_printer.py` | volcado legible |
| `SemanticAnalyzer` | `semantic/analyzer.py` | tipos + scopes |
| `CFGBuilder` | `cfg/builder.py` | grafo de flujo |
| `JsonSerializer` | `serialize/json_serializer.py` | AST → dict |

**Consecuencia al extender**: añadir un nodo nuevo obliga a añadir un método abstracto
`visit_*` y a implementarlo en **todos** los visitors. Olvidar uno rompe en tiempo de
construcción (método abstracto sin implementar), no en silencio. Esto es deliberado.

### 3.2 `inferred_type`: el canal entre semántico e IA

`Expression` (base) lleva un campo:

```python
inferred_type: Optional[str] = field(default=None, compare=False, repr=False, kw_only=True)
```

- `SemanticAnalyzer._eval(expr)` lo **rellena** al verificar tipos.
- `JsonSerializer` lo **lee** y lo emite como `"type"` en cada expresión del JSON.

Así el LLM recibe tipos **verificados por el compilador**, no inferidos del texto. Es el
mecanismo concreto que materializa "el compilador es la fuente de verdad". Si una fase
nueva produce expresiones, debe poblar `inferred_type` o el contexto del LLM queda incompleto.

### 3.3 Recolección de errores + tipo veneno

Requisito pedagógico: el analizador **no aborta en el primer error**, los junta todos en
una lista (`analyze() -> List[SemanticError]`). Para evitar cascadas de errores derivados,
una expresión mal tipada devuelve `None` (tipo "veneno"): cualquier operación sobre `None`
se suprime en vez de generar un segundo error falso.

**Regla al tocar `analyzer.py`**: toda comprobación de tipo debe cortocircuitar si algún
operando es `None`. Romper esto reintroduce errores en cascada.

### 3.4 Pre-pase de firmas

`visit_program` registra **todas** las firmas de función (`_declare_function`) **antes** de
visitar cualquier cuerpo. Por eso resuelven las llamadas hacia adelante y la recursión
(`factorial` se llama a sí misma). Cualquier resolución que dependa de declaraciones
globales debe ocurrir después de este pre-pase.

### 3.5 "Bloque actual = None" marca código inalcanzable

`CFGBuilder` hila un `self._current` (bloque en construcción). Tras `return`/`break`/
`continue` lo pone en `None`: las sentencias siguientes no se conectan a nada ⇒ quedan
**inalcanzables** por construcción, sin un pase aparte. Las aristas las gestiona una pila
`self._loops` de pares `(continue_target, break_target)`:

- `break` → salida del bucle,
- `continue` → cabecera (`while`) o bloque `update` (`for`),
- `if`/`else` → ramas `true`/`false` + convergencia `if.end` (omitida si ambas ramas terminan).

### 3.6 El documento JSON es la frontera

`serialize/document.py::serialize_program` ensambla el contrato entre el núcleo
sin-dependencias y la capa de IA. Claves de nivel superior: `functions` (firma, `params`,
`locals`, `ast` decorado, `cfg` embebido), `globals`, `diagnostics`.

`--json` lo emite **siempre**, incluso con errores (los errores van como `diagnostics`).
Por eso `--explain-error` funciona sobre programas que no compilan. **Todo lo que el LLM
ve pasa por aquí**: si un dato no está en este documento, el modelo no puede usarlo. Cambiar
la forma del JSON es cambiar el contrato del LLM — actualizar `context.py` en paralelo.

### 3.7 Anclaje del LLM y cliente inyectable

- `ai/prompts.py::SYSTEM` instruye al modelo a responder **solo** desde los datos formales,
  no inventar, en español, apto para lector de pantalla. Es la defensa contra alucinación.
- `ai/context.py` recorta, por consulta, solo la porción relevante del documento (función,
  variable + inicializador, resumen estructural, o diagnósticos + fuente). Menos ruido al modelo.
- `ai/assistant.py::Assistant` recibe el **cliente por inyección**. `test_ai.py` pasa un
  `FakeClient` que captura el prompt ⇒ se verifica la *selección de contexto* y el *enrutado*
  **sin red ni modelo**. Nunca exigir un LLM vivo en los tests.

### 3.8 Posición `línea:columna` de extremo a extremo

`LexerError`/`ParseError`/`SemanticError` llevan línea y columna exactas. No es cosmético:
alimenta directamente `--explain-error`. Cualquier nodo o error nuevo debe **propagar**
la posición o se rompe la explicación de errores.

---

## 4. Invariantes a no romper

1. **Núcleo stdlib-only.** Solo `pytest` como dependencia. La IA habla con Ollama por
   `urllib`, no por SDK. Import perezoso de `src/ai/`.
2. **Español** en comentarios, docstrings y salida de CLI.
3. **Visitor completo**: nodo nuevo ⇒ `visit_*` en todos los visitors.
4. **Recolectar errores, no abortar**; respetar el tipo veneno `None`.
5. **Poblar `inferred_type`** en expresiones nuevas.
6. **Propagar `línea:columna`** en tokens, nodos y errores.
7. **El JSON es el contrato**: cambiarlo ⇒ actualizar `context.py` y prompts.

---

## 5. Encaje con la propuesta

- Pipeline implementado 1:1 con el diagrama de `propuesta.md`.
- Las 3 fuentes de verdad (AST decorado, tabla de símbolos, CFG) construidas y serializadas.
- Las 4 consultas con los nombres de flag exactos que pide la propuesta.
- Principio "compilador = fuente de verdad, LLM = mediador" intacto (§3.2, §3.6, §3.7).
- Brechas restantes = fidelidad del modelo (§2), evaluación empírica y navegación interactiva.
