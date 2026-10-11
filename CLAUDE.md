# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development rules (authoritative — apply to ALL parts of the project)

`Rules.md` is the authoritative development-practices guide and governs every subject of this project — backend, frontend, tests, and docs alike (despite its name). Read it in full before writing or modifying code. In any conflict between a user request and these rules, alert the user, explain the conflict, and propose a compliant alternative rather than silently complying. Key non-negotiables:

- **Workflow scaled to the change (§6.0).** New feature → full workflow with two ⏸ gates; bug fix → short plan ⏸ + failing regression test first; trivial change (docs, config values, typo, dependency bump) → no gate, pre-commit must pass. When in doubt, use the more demanding workflow.
- **Blocking gates for a feature.** Two ⏸ gates require explicit user validation before proceeding:
  1. Present a structured action plan (need understanding, assumptions, SOLID/pattern rationale, ordered subtasks, impacted files, junctions, risks) — wait for "OK"/"go".
  2. Write E2E BDD scenarios in Gherkin (`Given/When/Then`, happy path + edge/error cases) in `tests/end_to_end/...`, executed with pytest-bdd — wait for validation. Validated scenarios are the contract; don't change them mid-flight without notifying the user.
- **TDD-first, always.** Red → Green → Refactor. Tests are written *before* production code and run to see them fail. Integration tests are written during development at each junction (never in bulk up front or at the end), and you write the junction's integration test before wiring two components together.
- **English only** for all code, tests, and docstrings.
- **Principles:** SOLID, DRY, KISS, YAGNI, Law of Demeter (no `a.b.c.d()` train wrecks; inject dependencies, don't reach through objects). Never add params/methods/abstractions "just in case", never create catch-all multi-responsibility classes.
- **Layout & test skeleton.** Source code in `src/<package>/` (src layout). The `tests/` tree mirrors source paths (without `src/`) under three roots — `tests/units/`, `tests/integration/`, `tests/end_to_end/`. One test file per source file (`model.py` → `test_model.py`), one test class per production class (`Model` → `TestModel`), method names `test_<method>_<context>_<expected_result>`, and every test method uses explicit `# Given / # When / # Then` blocks. Unit and integration test classes are `unittest.TestCase` classes run by pytest, following the mandatory `setUpClass/tearDownClass/setUp/tearDown` skeleton of §4.1; pytest-bdd step modules are plain functions.
- **Parameterization & configuration.** No hardcoded environment-dependent values: functions take them as parameters, values live in per-environment config files (`config/base.toml` + `local` / `docker` / `docker_prod`, selected by `APP_ENV`), read only through `src/<package>/settings.py`, which returns a typed, frozen, validated settings object built once in `main` (the composition root) and injected. Secrets come from env vars / `.env`, never from committed config. See §1.6 of the rules.
- **Logging & errors.** loguru only, configured once at the entry point; master level in `[logging] level`, overridable with `APP_LOG_LEVEL`; JSON logs in `docker_prod`. Package exception hierarchy in `exceptions.py`; no `print`, no bare `except`, no swallowed exception. See §1.7.
- **Containerization.** No Docker files in the template, but every project is dockerized as soon as it has a runnable entry point (uv multi-stage `Dockerfile` + `compose.yaml`, config selected via `APP_ENV`). See §1.8.
- Run the full review checklist (§7 of the rules) before delivering any code.

## Git & commits

- **Claude is not allowed to commit — under any pretext.** Claude never runs `git add`, `git commit`, or `git push` (nor any command that stages, rewrites, or publishes history). The user reviews and commits every change.
- At the end of a task, Claude states that the changes are ready to commit and proposes a [Conventional Commits](https://www.conventionalcommits.org/) message (`feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`).
- Branches: `main` + one branch per change (`feat/<topic>`, `fix/<topic>`, `chore/<topic>`, ...). `uv.lock` is committed, `.env` is ignored. See §9 of the rules.

## Environment

- **Package & dependency manager:** [uv](https://docs.astral.sh/uv/). Always go through uv (`uv add`, `uv sync`, `uv run …`) — never call `pip` or a bare `python` directly. Runtime dependencies via `uv add <pkg>`, dev tools via `uv add --dev <pkg>` (no upper version bounds; the lock file pins).
- **Python:** 3.13 or higher (`.python-version`).
- **Quality tooling:** `.pre-commit-config.yaml` is the single source of truth for **which** quality tools run and how they are invoked; per-tool **rule tuning** (Ruff ignores, pytest options, coverage settings, mypy paths) lives in `pyproject.toml`. Don't invoke or configure these tools anywhere else.

  | Concern | Tool | Hook id | Base rule |
  |---|---|---|---|
  | Secret detection | gitleaks | `gitleaks` | default ruleset |
  | Lint | Ruff | `ruff` | all rules, `--fix`, Google docstrings, targeted ignores in `pyproject.toml` |
  | Format | Ruff | `ruff-format` | — |
  | Type checking | mypy (mirrors-mypy) | `mypy` | `--disallow-untyped-defs`, `--ignore-missing-imports` |
  | Static security analysis | Bandit | `bandit` | severity ≥ medium, `tests/` excluded |
  | Complexity | Xenon | `xenon` | max absolute **B**, modules **A**, average **A** |
  | Markdown lint | markdownlint | `markdownlint` | `--fix` |
  | Tests | pytest + pytest-bdd (local hook) | `pytest` | runs `tests/` under coverage.py |
  | Coverage | coverage.py (local hook) | `coverage` | **≥ 70 %** (branch coverage) |

  `pytest`, `pytest-bdd`, `coverage` and `pre-commit` are dev dependencies (the `pytest` and `coverage` hooks run in the project's uv environment). mypy runs in an isolated environment: add third-party packages/stubs to the hook's `additional_dependencies` when needed.
- **Configuration:** per-environment config files (`local`, `docker`, `docker_prod`) read through a single loader — see `Rules.md` §1.6.
- **CI:** optional. The project must be fully verifiable locally through uv + pre-commit; a CI pipeline, if added, only replays the same commands.

## Project structure

```
config/                     # base.toml + local.toml / docker.toml / docker_prod.toml
src/template_project/
├── main.py                 # entry point & composition root (console script `template-project`)
├── settings.py             # the only config / env-var reader → frozen Settings
├── logging_setup.py        # loguru configuration
├── exceptions.py           # package exception hierarchy
└── models/application.py   # example domain model
tests/
├── units/template_project/...        # unittest classes, mocks for collaborators
├── integration/template_project/...  # junctions: settings ↔ config files, main ↔ settings ↔ logging
└── end_to_end/template_project/      # main.feature + pytest-bdd steps (app run as a subprocess)
```

For a **pure library** (no entry point): delete `main.py` and the `[project.scripts]` entry, and call `logger.disable("<package>")` in the package `__init__.py` — the calling application configures logging.

## Commands

All commands run from the repository root.

### Setup

```bash
uv sync                              # create .venv and install dependencies
uv run pre-commit install            # install the git hook (runs on every commit)
cp .env.example .env                 # then adjust local values / secrets
```

### Run

```bash
uv run template-project                          # default environment (local)
APP_ENV=docker_prod uv run template-project      # another environment
APP_LOG_LEVEL=DEBUG uv run template-project      # force the master log level
```

### Tests

```bash
uv run pytest tests/                                        # full suite
uv run pytest tests/units/                                  # one level: units / integration / end_to_end
uv run pytest tests/units/<path>/test_<module>.py           # one test file
uv run pytest tests/units/<path>/test_<module>.py::Test<Class>::test_<method>   # one test
uv run coverage run -m pytest tests/ && uv run coverage report   # with coverage (threshold from pyproject.toml)
```

### Lint, format, types, complexity, security, secrets, tests (pre-commit)

```bash
uv run pre-commit run --all-files                  # every hook on the whole repo (same gate as a commit)
uv run pre-commit run <hook-id> --all-files        # a single hook: gitleaks, ruff, ruff-format, mypy, bandit, xenon, markdownlint, pytest, coverage
uv run pre-commit run pytest --all-files && uv run pre-commit run coverage --all-files   # tests + 70 % threshold only
uv run pre-commit run --files <path> [<path> ...]  # only on given files (also works on untracked files)
uv run pre-commit autoupdate                       # bump hook versions
```

`--all-files` only sees files tracked by git; before the first commit, use `--files $(git ls-files --others --exclude-standard)`.

### Windows notes

- If pre-commit fails with `UnicodeDecodeError: 'charmap'`, run it in UTF-8 mode: `PYTHONUTF8=1 uv run pre-commit ...` (or set `PYTHONUTF8=1` permanently in the user environment).
- If uv fails with `invalid peer certificate: UnknownIssuer` (TLS inspection by an antivirus or proxy), add `--system-certs` to the uv command.
