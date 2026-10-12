# templateProject

A minimal, working Python project template that applies the rules in [`principles.md`](principles.md):
TDD (unit / integration / BDD end-to-end tests), SOLID, per-environment configuration, loguru logging,
and a pre-commit quality gate (Ruff, mypy, Bandit, Xenon, gitleaks, markdownlint, coverage ≥ 70 %).

The example package (`src/template_project/`) is deliberately tiny: it loads the configuration of the
selected environment, configures logging, and announces that the application started. Every rule of
`principles.md` has a concrete example in it.

## Start a new project from this template

1. Copy the repository (without `.git/` and `.venv/`) into a new folder, then `git init`.
2. Rename the package — `template_project` / `template-project` appear in:
   - `src/template_project/` and `tests/{units,integration,end_to_end}/template_project/` (folder names);
   - `pyproject.toml` (`name`, `[project.scripts]`, `[tool.coverage.run] source`);
   - `config/base.toml` (`[app] name`);
   - imports and expected values in the tests, `CLAUDE.md`, and this README.

   List every occurrence with: `git grep -n -e template_project -e template-project`
3. Set up the environment:

   ```bash
   uv sync
   uv run pre-commit install
   cp .env.example .env
   uv run pre-commit run --files $(git ls-files --others --exclude-standard)   # everything green before the first commit
   ```

4. Replace the example (`models/application.py`, `main.feature`, ...) feature by feature, following the
   workflow of `principles.md` §6.

### Pure library variant

If the project is a library with no entry point: delete `main.py`, the `[project.scripts]` entry and the
end-to-end example, and call `logger.disable("<package>")` in the package `__init__.py` so that the calling
application decides how to log.

## Run

```bash
uv run template-project                       # APP_ENV defaults to "local"
APP_ENV=docker_prod uv run template-project   # JSON logs, WARNING level
APP_LOG_LEVEL=DEBUG uv run template-project   # force the master log level
```

## More

- [`principles.md`](principles.md) — development rules (workflow, tests, configuration, logging, git).
- [`CLAUDE.md`](CLAUDE.md) — guidance for Claude Code and every development command.
