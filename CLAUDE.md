# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Two coupled artifacts for an academic project on **AI-augmented compilers for accessibility** (UNSA, compilers course):

1. **The paper** (repo root) — IEEE conference LaTeX (`IEEE-conference-template-062824.tex`) plus the Spanish proposal `propuesta.md`. The paper is the deliverable; the code is its prototype.
2. **The prototype** (`project/`) — **MiniLang**, a statically-typed imperative language and its compiler frontend written in Python 3.11+ with no runtime dependencies (only `pytest` for tests).

The end goal (per `propuesta.md`) is **SemanticC**: a CLI that exposes a compiler's internal representations (tokens, AST, symbol table, CFG) to an LLM so it answers natural-language questions anchored in formal semantics rather than raw source. The compiler is the source of truth; the LLM only verbalizes verified structure.

## Project status (read before extending the compiler)

`project/README.md` is the user-facing entry doc (install, all CLI commands, language overview). `project/STATUS.md` is the authoritative progress tracker — update it when a phase lands. Current state (~90% of proposal):

- **Done**: Lexer, Parser, AST + Visitor pattern, ASTPrinter, Semantic analyzer + Symbol table (`src/semantic/`), CFG generation (`src/cfg/`), JSON serialization (`src/serialize/`), LLM integration via Ollama (`src/ai/`) with `--explain-function`/`--describe`/`--explain-error`/`--navigate`, 146 passing tests.
- **Pending (future work)**: response-quality tuning (bigger model / few-shot prompts), interactive accessible navigation, empirical user study, lexer/parse-error explanation in the AI layer.

When adding a phase, follow the pipeline already documented in `propuesta.md` and `STATUS.md`: `Lexer → Parser → AST → [Semantic → CFG → Symbol Table] → AI layer`. Keep the new-phase rationale consistent with that design (language-agnostic architecture, pedagogically rich diagnostics).

## Commands

All commands run from `project/`. The repo uses a local venv at `project/.venv`.

```bash
cd project

# Setup
python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run the compiler frontend: lex + parse + print AST
.venv/bin/python main.py samples/factorial.ml

# Show only the token stream (skips parsing)
.venv/bin/python main.py --tokens samples/hello.ml

# Other phase dumps
.venv/bin/python main.py --symbols samples/factorial.ml   # symbol table
.venv/bin/python main.py --cfg     samples/control_flow.ml # control-flow graph
.venv/bin/python main.py --json    samples/factorial.ml   # LLM-context JSON

# Natural-language queries (need `ollama serve` + `ollama pull llama3.2:3b`)
.venv/bin/python main.py --explain-function factorial samples/factorial.ml
.venv/bin/python main.py --describe resultado samples/factorial.ml
.venv/bin/python main.py --explain-error samples/type_error.ml
.venv/bin/python main.py --navigate samples/factorial.ml

# Tests
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m pytest tests/test_parser.py -v          # one suite
.venv/bin/python -m pytest tests/test_lexer.py::test_name   # one test
```

Building the paper (root): standard `pdflatex IEEE-conference-template-062824.tex`; `IEEEtran.cls` is vendored locally.

## Architecture

The compiler is a classic two-phase recursive-descent frontend. Key design choices that span files:

- **`src/lexer/tokens.py`** — single source of truth for the token vocabulary: `TokenType` enum (68 types), `Token` dataclass (carries `line`/`column`), and the `KEYWORDS` map. Add new keywords/operators here first.
- **`src/lexer/lexer.py`** — `Lexer.tokenize()` produces the token list. Handles compound operators (`==`, `+=`, …), string escapes, line (`//`) and block (`/* */`) comments. Raises `LexerError` with exact `line:column`.
- **`src/parser/parser.py`** — `Parser.parse()` returns a `Program` AST. Hand-written recursive descent; the **complete EBNF grammar is in the module docstring** — keep it in sync when changing parse rules. Operator precedence is encoded as the descent chain `assignment → logic_or → logic_and → equality → comparison → term → factor → unary → primary`. Raises `ParseError`.
- **`src/parser/ast_nodes.py`** — 20+ frozen-ish dataclass nodes under `Node → Statement | Expression`, plus the abstract `Visitor` interface. **The Visitor pattern is load-bearing**: every pass (semantic analysis, CFG, JSON serialization) is a new `Visitor` subclass, so adding a node requires adding a `visit_*` abstract method and updating all visitors (`ASTPrinter`, `SemanticAnalyzer`). `Expression` nodes carry an `inferred_type` field that `SemanticAnalyzer` fills in.
- **`src/semantic/`** — `symbols.py` (`Symbol`/`Scope`/`SymbolTable`, a stack of nested scopes) and `analyzer.py` (`SemanticAnalyzer`, the 2nd `Visitor`). Strict type checking (no int↔float coercion); **collects all errors into a list** rather than raising on first (project requirement — pedagogical diagnostics for the LLM); uses `None` as a poison type to suppress cascade errors. A pre-pass registers all function signatures so forward calls and recursion resolve.
- **`src/cfg/`** — `blocks.py` (`BasicBlock`, `Edge`, `ControlFlowGraph`, `format_cfg`) and `builder.py` (`CFGBuilder`, the 3rd `Visitor`). Builds **one CFG per function**. Threads a "current block" that becomes `None` after `return`/`break`/`continue` (marks unreachable code); `if`/`while`/`for` create branch/merge/back-edges; `break`→loop exit, `continue`→header (while) or update block (for). Expressions are atomic (no short-circuit branching). CLI `--cfg`.
- **`src/serialize/`** — `json_serializer.py` (`JsonSerializer`, the 4th `Visitor`: AST node → JSON-compatible dict, each expression carrying its `type`) and `document.py` (`serialize_program`: assembles the **LLM-context document** — `functions` with signature/params/locals/decorated-AST/embedded-CFG, `globals`, `diagnostics`). CLI `--json` emits it **always**, errors included as diagnostics (so `--explain-error`-style queries work on failing programs). This JSON is the boundary between the dependency-free compiler core and the LLM layer.
- **`src/ai/`** — the AI layer (only `urllib`, no new deps; imported lazily so the core stays dependency-free and offline-testable). `client.py` (`OllamaClient` → self-hosted Ollama at `localhost:11434`, configurable via `OLLAMA_HOST`/`MINILANG_MODEL`, default `llama3.2:3b`), `context.py` (per-query slicing of the JSON document), `prompts.py` (Spanish system prompt that **anchors** the model to the compiler's formal data — no hallucination), `assistant.py` (`Assistant` orchestrator with an **injectable client** — tests pass a fake, see `test_ai.py`). CLI query flags route through `run_ai_query` in `main.py`, which needs `ollama serve` running and the model pulled.
- **`src/errors.py`** — `LexerError` / `ParseError`, both formatted as `line:column`. Positional accuracy is a project requirement (errors feed the LLM "explain-error" feature), so preserve line/column through any new code.
- **`main.py`** — thin CLI orchestrator: reads file → `compile_source()` runs lexer then parser then ASTPrinter. New query flags (`--explain-function`, `--navigate`, etc. from the proposal) attach here.

`samples/*.ml` are canonical MiniLang programs (`hello`, `factorial`, `control_flow`) used both as docs and informal fixtures.

## Conventions

- Code comments, docstrings, and CLI output are in **Spanish** — match this for consistency.
- Everything must stay **dependency-free** (only stdlib); `pytest` is the sole allowed dependency. The AI layer talks to Ollama over `urllib`, not an SDK — keep it that way. The external service (Ollama) is a runtime requirement for the query flags, not a Python dependency.
- `.history/` holds editor auto-saved snapshots — ignore it; never edit files there.
