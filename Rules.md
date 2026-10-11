# Development Best Practices Guide

---

## Mission

As a development assistant, you must:

- **Produce clean, testable, maintainable, and scalable code.**
- **Rigorously apply the principles set out below.**
- **Refuse or warn when a request goes against these practices, and propose a compliant alternative.**
- **Always reason TDD-first: tests before production code.**
- **Always present an action plan before writing a single line of code, and wait for the user's validation** (scaled to the size of the change, see §6.0).
- **Always write tests, code, and docstrings in English.**
- **Parameterize functions and keep environment-dependent values in configuration files** (§1.6).
- **Log through loguru and handle errors explicitly** (§1.7).
- **Never stage, commit, or push: the user owns every commit** (§9).

---

## 1. Core Principles

### 1.1 SOLID

Every class and module must respect the five SOLID principles:

| Principle | Definition |
|---|---|
| **S — Single Responsibility** | One class = one single reason to change. |
| **O — Open/Closed** | Open for extension, closed for modification. |
| **L — Liskov Substitution** | A subclass must be substitutable for its parent class without breaking behavior. |
| **I — Interface Segregation** | Prefer multiple specific interfaces over a single general-purpose one. |
| **D — Dependency Inversion** | Depend on abstractions, not on concrete implementations. |

### 1.2 DRY (Don't Repeat Yourself)

- Any duplicated logic must be extracted into a reusable function, method, or class.
- Before writing a new function, check whether an equivalent already exists.

### 1.3 KISS (Keep It Simple, Stupid)

- Favor the simplest solution that meets the need.
- Avoid premature abstractions.
- One function = one clear, readable intent.

### 1.4 YAGNI (You Aren't Gonna Need It)

- Write only what is necessary for the current User Story / need.
- No "just in case" code, no unused parameters or methods.

### 1.5 Law of Demeter (Principle of Least Knowledge)

- An object should only talk to its "close friends".
- Avoid chains like `object.attribute.sub_attribute.method()` (train wrecks).
- Prefer exposing high-level methods that encapsulate internal access.

```python
# Bad - violates the Law of Demeter
total = order.customer.address.city.zip_code

# Good - encapsulation
total = order.get_shipping_zip_code()
```

### 1.6 Parameterization & Configuration

Code must be configurable without being edited. A user must be able to change behavior, or switch from one environment to another, by editing or selecting a configuration file only.

**Parameterize functions**

- No hardcoded values in business logic: paths, URLs, hosts, ports, timeouts, thresholds, limits, model names, feature flags, etc. become function/constructor parameters.
- Parameters carry explicit type hints and, when a sensible default exists, a default value.
- Functions receive their values from the caller (dependency injection, see DIP) — they never read the configuration or environment variables themselves.
- YAGNI still applies: externalize what varies between environments or what a user may legitimately tune, not every literal.

**Configuration files**

- One configuration directory with a shared base and one override file per environment:

```
config/
├── base.toml           # defaults shared by every environment
├── local.toml          # local development (default)
├── docker.toml         # docker (dev/test) environment
└── docker_prod.toml    # docker production
```

- The active environment is selected by a single environment variable, `APP_ENV=local|docker|docker_prod` (default `local`). The environment file is merged over `base.toml`. Adding an environment = adding a file; the available environments are the files present.
- A few targeted environment-variable overrides are allowed for operational knobs (e.g. `APP_LOG_LEVEL`), and only through the loader.
- Secrets (tokens, passwords, API keys) **never** go into configuration files committed to the repository: they come from environment variables or a non-committed `.env` file, with a committed `.env.example` listing the expected keys.
- TOML read with the standard library `tomllib` (no extra dependency).

**Configuration-reading functions**

- A single, dedicated module (`src/<package>/settings.py`) is the only place that reads configuration files and environment variables.
- It exposes small, single-purpose functions:
  - `get_environment(environ: Mapping[str, str]) -> str` — resolves the active environment.
  - `load_config(environment: str, config_dir: Path, environ: Mapping[str, str]) -> Settings` — reads `base.toml`, merges the environment file, applies environment-variable overrides.
- The environment variables are **injected** as a `Mapping` (the entry point passes `os.environ`), so the loader is testable without touching the real environment.
- It returns a **typed, immutable** settings object (frozen `dataclass`), never a raw `dict` passed around the codebase.
- It **validates at startup and fails fast** with an explicit error message (missing file, missing key, wrong type, unknown environment, invalid value).
- The settings object is built once at the entry point (`main`, the composition root) and its values are injected into the components that need them.
- The loader itself is unit-tested (merge order, overrides, validation errors) and integration-tested against the real `config/` files.

```python
# Bad - hardcoded value, hidden configuration read
def fetch_items():
    return requests.get("http://localhost:8000/items", timeout=5)


# Good - parameterized; values come from the injected settings
def fetch_items(base_url: str, timeout_seconds: float) -> Response:
    return requests.get(f"{base_url}/items", timeout=timeout_seconds)


settings = load_config(get_environment(os.environ), Path("config"), os.environ)
fetch_items(settings.api_base_url, settings.api_timeout_seconds)
```

### 1.7 Logging & Error Handling

**Logging (loguru)**

- All logging goes through [loguru](https://github.com/Delgan/loguru): `from loguru import logger`. No `print` (enforced by Ruff `T20`), no stdlib `logging` configuration.
- Logging is configured **once**, at the entry point, by a dedicated function (`configure_logging(settings, sink)`); no other module adds or removes handlers.
- A **master log level** lives in the configuration and filters every handler:

```toml
[logging]
level = "INFO"        # TRACE | DEBUG | INFO | SUCCESS | WARNING | ERROR | CRITICAL
serialize = false     # true = one JSON object per log line
file_path = ""        # empty = stderr only; otherwise also write to this file
rotation = "10 MB"
retention = "14 days"
```

- Default levels per environment: `local` → `DEBUG`, `docker` → `INFO`, `docker_prod` → `WARNING` with `serialize = true` (structured JSON logs).
- The level can be forced at run time with `APP_LOG_LEVEL`, without editing any file; an invalid level fails fast.
- Use the right level: `DEBUG` for diagnostic details, `INFO` for business milestones, `WARNING` for recoverable anomalies, `ERROR` for failures, `CRITICAL` for unrecoverable states.
- Use loguru's lazy formatting (`logger.info("User {} created", user_id)`), never f-strings in log calls.
- Never log secrets or personal data.
- **Pure libraries** (no entry point) never configure logging: they call `logger.disable("<package>")` in their `__init__.py` and let the calling application decide.
- Tests capture logs through an injected sink (e.g. `io.StringIO`) and remove handlers in `tearDown` (`logger.remove()`).

**Error handling**

- Each package defines its own exception hierarchy in `exceptions.py`: one base class (`<Package>Error`) and specific subclasses (`ConfigurationError`, `ValidationError`, ...).
- Raise the most specific exception, with an explicit message stored in a variable first (Ruff `EM`/`TRY003`).
- Never use a bare `except:` or `except Exception:` that swallows the error. Either log and re-raise, translate it into a domain exception (`raise DomainError(...) from error`), or handle it meaningfully.
- Only the entry point catches the package base exception, logs it, and turns it into an exit code.

### 1.8 Containerization

- Every project is dockerized **as soon as it has a runnable entry point** (typically with the first delivered feature), not at the end.
- The template ships no Docker files, because their structure depends on the project. When dockerizing, add:
  - a multi-stage `Dockerfile` based on uv (`uv sync --frozen --no-dev` in the build stage, slim runtime image, non-root user);
  - a `compose.yaml` with one service per relevant environment.
- The container selects its configuration **only** through `APP_ENV=docker|docker_prod`; secrets come from environment variables or compose secrets, never copied into the image.
- The container runs the same `uv` commands as local development — no parallel tooling.

---

## 2. Design Patterns

Use the appropriate design patterns when the context justifies it. **Never force a pattern.**

### Recommended patterns by need

- **Creational:** Factory, Builder, Singleton (sparingly), Abstract Factory
- **Structural:** Adapter, Decorator, Facade, Composite, Proxy
- **Behavioral:** Strategy, Observer, Command, State, Template Method, Chain of Responsibility
- **Architectural:** Repository, Dependency Injection, Composition Root, MVC / MVP / MVVM, Hexagonal (Ports & Adapters), CQRS

**Rule:** before proposing a pattern, justify in one sentence why it solves the problem here.

---

## 3. TDD (Test-Driven Development)

Every development follows the Red → Green → Refactor cycle:

1. **Red:** write a failing test (the behavior does not yet exist) and run it to see it fail.
2. **Green:** write the **minimal** code needed to make the test pass.
3. **Refactor:** improve the code without breaking the tests.

**The AI must always write the tests BEFORE the production code.**

---

## 4. Test Structure

### 4.1 Mandatory skeleton for a test class

Unit and integration tests are `unittest.TestCase` classes, **run by pytest**. Every test class must follow exactly this structure:

```python
import unittest

from my_package.models.model import Model


class TestModel(unittest.TestCase):
    simple_model: Model  # attributes set in setUpClass are declared for mypy

    @classmethod
    def setUpClass(cls) -> None:
        """
        Execute before all tests.
        Set up global variables or global configuration for all unit tests
        in the class.
        If the data change in one test, the data change for all tests.
        """
        cls.simple_model = Model("Test")

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test."""

    def tearDown(self) -> None:
        """Execute at the ending of each test."""

    def test_get_name_when_model_initialized_returns_expected_name(self) -> None:
        # Given
        model = self.simple_model

        # When
        name = model.get_name()

        # Then
        self.assertEqual(name, "Test")
```

### 4.2 Test writing rules

- One test class per production class (`Model` → `TestModel`).
- One test file per source file (`model.py` → `test_model.py`).
- Every test method follows the **Given / When / Then** pattern (materialized through comments; `# When / Then` is allowed for `assertRaises` blocks).
- Explicit test names: `test_<method>_<context>_<expected_result>`.
  - Example: `test_get_name_when_model_initialized_returns_expected_name`
- One test = one single behavior verified.
- Tests must be independent of each other (execution order must not matter); global state (cwd, environment variables, loguru handlers) is restored in `tearDown`.
- Prefer mocks/stubs to isolate the class under test from its dependencies.
- Test methods are type-annotated (`-> None`): mypy checks the tests too.

### 4.3 End-to-end tests (BDD)

- E2E scenarios are Gherkin `.feature` files executed with **pytest-bdd**, in the same `uv run pytest` run.
- The step definitions live in a `test_<module>.py` next to the `.feature` file. Step modules are plain functions and fixtures: the class skeleton of §4.1 does not apply to them.
- E2E tests exercise the system as a user would (e.g. the installed console script in a subprocess, in a temporary working directory).

---

## 5. Test Folder Architecture

The source code uses the **src layout** (`src/<package>/`). The `tests/` folder structure must **faithfully mirror the source code structure**, and be organized into three levels:

```
tests/
├── units/              # Unit tests (fast, isolated)
│   └── ...
├── integration/        # Integration tests (interactions between components)
│   └── ...
└── end_to_end/         # E2E tests (complete user/system journeys)
    └── ...
```

### 5.1 Concrete example

**Source code:**

```
src/
└── my_package/
    ├── models/
    │   └── model.py
    ├── services/
    │   └── service.py
    └── domain/
        └── domain.py
```

**Corresponding unit tests:**

```
tests/
└── units/
    └── my_package/
        ├── models/
        │   └── test_model.py
        ├── services/
        │   └── test_service.py
        └── domain/
            └── test_domain.py
```

### 5.2 Rules

- A test's path must mirror the path of its source file (without the `src/` prefix), prefixed by `tests/units/`, `tests/integration/` or `tests/end_to_end/` depending on the test level.
- Test directories are not packages (no `__init__.py`); pytest runs with `--import-mode=importlib` so identical file names can exist at several levels.
- Prefix every test file with `test_`.
- Prefix every test class with `Test`.
- Prefix every test method with `test_`.

---

## 6. Mandatory Workflow

### 6.0 Scale the workflow to the change

| Change | Workflow |
|---|---|
| **New feature** (or a change of user-visible behavior) | The full 9 steps below, with both ⏸ gates. |
| **Bug fix** | Short plan (cause, fix, impacted files) ⏸ → a failing regression test reproducing the bug (Red) → fix (Green) → refactor → full suite. The BDD gate applies only if the visible behavior changes. |
| **Trivial change** (docs, comments, config values, typo, dependency bump) | No gate; `uv run pre-commit run --all-files` must pass. |

When in doubt, use the more demanding workflow.

### 6.1 New feature: the 9 steps

The AI must strictly and in order follow the steps below. The ⏸ steps are **blocking**: no line of code is written until validation from the user.

> **Guiding principle:** integration tests are written **during development**, not upfront.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Step 1 : ACTION PLAN ─────────────────────────────► ⏸ User validation │
│ Step 2 : BDD SCENARIOS (E2E Gherkin tests) ───────► ⏸ User validation │
│ Step 3 : UNIT TESTS (Red) - per subtask                              │
│ Step 4 : PRELIMINARY INTEGRATION TESTS                               │
│          (only if existing code to plug into / if relevant)          │
│ Step 5 : UNIT CODE (Green) - subtask implementation                  │
│ Step 6 : INTEGRATION TESTS (Red) - junctions between subtasks        │
│ Step 7 : INTEGRATION CODE (Green) - wiring components together       │
│ Step 8 : REFACTOR                                                    │
│ Step 9 : FINAL VERIFICATION & RECAP                                  │
│                                                                      │
│     └── TDD loop per subtask: Steps 3 → 5 repeat for each subtask,   │
│         then Steps 6 → 7 for each junction.                          │
└──────────────────────────────────────────────────────────────────────┘
```

#### Step 1 — Action Plan ⏸

The AI presents a structured action plan to the user and waits for explicit validation before any further step.

The plan must contain at minimum:

1. **Understanding of the need** Rephrasing of the requested feature, in one to three sentences, using the domain vocabulary.
2. **Questions / assumptions** Gray areas, default assumptions made, decisions worth confirming.
3. **Technical approach**
   - SOLID principles involved and why.
   - Design pattern(s) considered, with a one-sentence justification.
   - Impacts on the existing architecture (layers touched, dependencies added).
4. **Subtask breakdown** Numbered, ordered list of subtasks composing the feature.
5. **Impacted files**
   - Created files (full path).
   - Modified files (full path + nature of the change).
   - Associated test files (E2E, units, integration).
6. **Identified junctions** List of connections between components that will need to be validated by integration tests during development.
7. **Risks & points of attention** Potential trade-offs, technical debt, external dependencies.

**Validation rules:**

- The AI does not move on to Step 2 until the user has explicitly validated (e.g., "OK", "approved", "go").
- If the user asks for adjustments, the AI updates the plan and requests validation again.

#### Step 2 — End-to-End Scenarios in BDD Format ⏸

Before any development, the AI writes the E2E tests as BDD scenarios (Behavior Driven Development) in Gherkin syntax.

These scenarios must:

- Describe the expected behavior from the end user's / system's perspective.
- Cover the happy path and error / edge cases.
- Be placed in `tests/end_to_end/...` (respecting the source code structure).
- Be written in **business language**, readable by a non-developer.

**Example BDD scenario:**

```gherkin
Feature: Creating a model in the system

  Scenario: Successful creation of a model with valid parameters
    Given a system initialized with no existing model
    When I create a model named "Test"
    Then the model "Test" is registered in the system

  Scenario: Creation failure with an empty name
    Given an initialized system
    When I try to create a model with an empty name
    Then a validation error is raised
    And no model is registered
```

**The AI requests validation of the BDD scenarios from the user before continuing.**

> The validated scenarios become the contract the final code must satisfy. Any evolution of the need must go through an update of the scenarios, notified to and validated by the user.

#### Step 3 — Unit Tests (TDD - Red)

For the current subtask (iterating subtask by subtask):

- Write the unit tests in `tests/units/...`.
- Strictly respect the folder structure (section 5) and the mandatory skeleton (section 4.1).
- Cover the correct behavior of each small unit (method, class) in isolation (mocks/stubs for dependencies).
- Nominal cases + edge cases + error cases.
- The tests must fail initially (Red phase of TDD) — run them and see them fail.

#### Step 4 — Preliminary Integration Tests *(conditional)*

This step is executed ONLY if:

- the current subtask must plug into existing code in the project,
- OR it is relevant to characterize the expected behavior of an integration with an already-in-place third-party component before coding.

In that case:

- Write an integration test in `tests/integration/...` describing how the new unit will plug into the existing code.
- This test fails until the new unit exists (Red).

Otherwise, skip this step and go directly to Step 5.

#### Step 5 — Unit Code (TDD - Green)

- Implement the minimal code needed to make the subtask's unit tests (Step 3) pass.
- And, where applicable, make the preliminary integration tests from Step 4 pass.
- Run the tests to check for non-regression on the rest of the code.

> Once the subtask is green, go back to Step 3 for the next subtask, until all subtasks of the plan are implemented.

#### Step 6 — Junction Integration Tests (Red)

Once several subtasks are implemented, write the integration tests in `tests/integration/...` for each junction identified in the plan (Step 1, point 6):

- Verify the interactions and connections between components (services ↔ models, services ↔ domains, controller ↔ service, loader ↔ configuration files, etc.).
- Cover the flows that span multiple subtasks of the feature.
- Use doubles only for dependencies that are external to the system (third-party APIs, etc.), according to the project's strategy.
- The tests must fail initially (Red) since the wiring does not yet exist.

#### Step 7 — Integration Code (Green)

- Implement the wiring between components to make the integration tests from Step 6 pass.
- **Keep the implementation minimal**: this code only connects what already exists.
- Run all tests (unit + integration) to check for non-regression.

#### Step 8 — Refactor (TDD - Refactor)

- Improve the code quality without changing its behavior (tests stay green).
- Apply the SOLID, DRY, KISS, YAGNI, Demeter principles.
- Justify refactoring choices.

#### Step 9 — Final Verification & Recap

- Run the entire test suite: unit → integration → E2E.
- Run `uv run pre-commit run --all-files`.
- Walk through the code review checklist (section 7).
- Report any potential violation or trade-off made.
- Provide a recap of what was delivered (created/modified files, added tests, open points) and a proposed Conventional Commit message — **the user commits** (§9).

---

## 7. Code Review Checklist

Before delivering any portion of code, verify that:

- [ ] The workflow matching the size of the change was followed (§6.0).
- [ ] An action plan was presented and **validated** by the user before any development.
- [ ] The BDD scenarios (E2E) were written and **validated** before any code was written.
- [ ] The E2E tests cover the **happy path AND error / edge cases**.
- [ ] Each subtask of the plan has its dedicated **unit tests** (written before the code).
- [ ] **Integration tests** validate each **junction between components** identified in the plan.
- [ ] Integration tests were written **during development** (Red → Green), not in bulk at the end of the feature.
- [ ] Every class has a **single responsibility**.
- [ ] No duplicated logic (DRY).
- [ ] No undemanded functionality added (YAGNI).
- [ ] The code is readable without superfluous comments (KISS).
- [ ] No deep call chains (Demeter).
- [ ] Dependencies are passed through injection (DIP); only the entry point wires components together.
- [ ] No hardcoded environment-dependent values: functions are parameterized and values come from the configuration files (§1.6).
- [ ] Configuration is read only through the dedicated loader, validated at startup, and works for every environment (`local`, `docker`, `docker_prod`).
- [ ] No secret is committed in a configuration file.
- [ ] Logging goes through loguru, configured once at the entry point, with the level taken from the configuration (§1.7).
- [ ] Errors use the package exception hierarchy; no swallowed exception, no bare `except`.
- [ ] The project is dockerized once it has a runnable entry point (§1.8).
- [ ] `uv run pre-commit run --all-files` passes (secrets, lint, format, types, complexity, security, markdown, tests, coverage ≥ 70 %).
- [ ] The unit test structure follows the mandatory skeleton.
- [ ] The `tests/units/...`, `tests/integration/...`, `tests/end_to_end/...` structure mirrors the source code.
- [ ] Names (variables, methods, classes) are explicit and consistent with the domain.
- [ ] Code, tests, and docstrings are written in English.
- [ ] Nothing was staged, committed, or pushed by the AI (§9).

---

## 8. What the AI Must NEVER Do

- ❌ Start coding a feature without having presented and gotten validation for an action plan.
- ❌ Write production code for a feature without having gotten validation for the BDD scenarios (E2E) beforehand.
- ❌ Write code without an associated test (unit and integration when relevant).
- ❌ Write all integration tests in bulk at the start or end of a feature: they must be written during development, at each junction.
- ❌ Wire two components together without first writing the integration test for their junction.
- ❌ Propose a "catch-all" class that handles multiple responsibilities.
- ❌ Duplicate code to go faster.
- ❌ Add parameters, methods, or abstractions "just in case".
- ❌ Place test files outside the prescribed folder structure.
- ❌ Omit the `Given / When / Then` blocks in tests.
- ❌ Modify validated BDD scenarios mid-flight without notifying the user.
- ❌ Write tests, code, or docstrings in any language other than English.
- ❌ Ignore a principle violation without reporting it to the user.
- ❌ Hardcode a path, URL, port, threshold, or any environment-dependent value in business logic.
- ❌ Read configuration files or environment variables outside the dedicated configuration loader.
- ❌ Commit secrets in configuration files.
- ❌ Use `print` or configure logging anywhere but the entry point.
- ❌ Swallow an exception or use a bare `except`.
- ❌ Bypass the pre-commit hooks (`--no-verify`) or lower their thresholds without the user's agreement.
- ❌ Run `git add`, `git commit`, or `git push` — under any pretext.

---

## 9. Git & Commits

- Every project is a git repository from day one (`git init`), with `main` as the main branch.
- One branch per change: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`, `refactor/<topic>`, `test/<topic>`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat: ...`, `fix: ...`, `test: ...`, `refactor: ...`, `docs: ...`, `chore: ...`.
- `uv.lock` is committed; `.env` is ignored (`.gitignore`), `.env.example` is committed.
- The pre-commit hooks run on every commit and must pass.
- **The AI never stages, commits, or pushes, under any pretext.** It ends its work by stating that the changes are ready and proposing a Conventional Commit message; the user reviews and commits.
