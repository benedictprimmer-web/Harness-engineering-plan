# harness-cli

## Project

A command-line tool that installs and audits Claude Code harnesses for any software project. Distributed as a Python package on PyPI. Users install it with `pip install harness-cli` and run `harness install /path/to/project` or `harness audit /path/to/project`.

## Stack

- **Runtime**: Python 3.11+
- **CLI framework**: Typer 0.12 (Click-based, auto-generates help)
- **Packaging**: Hatch (`pyproject.toml`); published via GitHub Actions to PyPI
- **Testing**: pytest + pytest-tmp-path for filesystem tests
- **Linting**: ruff + mypy

## Commands

```bash
pip install -e ".[dev]"         # install with dev deps (editable)
harness --help                  # try the CLI
harness install /tmp/myproject  # run the installer
harness audit /tmp/myproject    # run the audit

pytest                          # run all tests
pytest tests/test_install.py -v # run a specific test file
ruff check . && mypy src/       # lint + type check
ruff check --fix .              # auto-fix lint issues
hatch build                     # build sdist + wheel
```

## Architecture

```
src/
  harness_cli/
    __init__.py     ← package version
    cli.py          ← Typer app — entry points: install, audit, history
    install.py      ← project detection + file generation logic
    audit.py        ← five-layer harness scorer
    templates/      ← embedded template files (copied to target projects)
tests/
  test_install.py   ← filesystem tests using tmp_path fixture
  test_audit.py     ← scoring accuracy tests
  fixtures/         ← sample project dirs (python-fastapi/, node-next/, etc.)
pyproject.toml      ← Hatch config, dependencies, entry points, ruff/mypy settings
```

## Conventions

- **Think Before Coding**: state assumptions, ask when uncertain, never silently guess
- **Simplicity First**: minimum code that solves the problem; no speculative abstractions
- **Surgical Changes**: touch only what the task requires; don't improve adjacent code
- **Goal-Driven Execution**: convert vague requests into verifiable success criteria first
- **Entry point**: the Typer app in `cli.py` should stay thin — logic lives in `install.py` and `audit.py`.
- **Templates**: embedded templates live in `src/harness_cli/templates/`. Access them with `importlib.resources.files("harness_cli") / "templates"` — not with file paths.
- **Filesystem tests**: all tests that write files use `tmp_path` (pytest fixture). Never write to the real filesystem in tests.
- **CLI errors**: use `typer.echo(msg, err=True)` + `raise typer.Exit(1)` instead of `sys.exit()`.
- **Type annotations**: every public function needs a return type annotation. Mypy runs in strict mode.

## Environment

No environment variables required for normal use. For publishing:
- `PYPI_TOKEN` — PyPI API token (GitHub Actions secret; get from team 1Password vault)
- `TEST_PYPI_TOKEN` — TestPyPI token for release candidate testing

## Gotchas

- **Editable install required for tests**: tests import `harness_cli` — if you haven't run `pip install -e .`, imports will fail with a confusing "module not found" error even though the files exist.
- **Templates use importlib.resources**: do not use `Path(__file__).parent / "templates"` — this breaks when the package is installed as a zip (common in some envs). Always use `importlib.resources.files()`.
- **Typer vs Click**: Typer wraps Click. If you need access to the underlying Click context, use `typer.Context` as a parameter — not `click.get_current_context()`.
- **PyPI publish is irreversible**: once a version is published to PyPI, that version string is permanent even if deleted. Always test on TestPyPI first: `hatch publish --repo test`.
- **`hatch build` before publish**: the GitHub Actions workflow does this automatically, but local testing with `pip install dist/*.whl` requires a fresh build.
- **mypy `--strict` rejects Optional without annotation**: `def foo(x=None)` must be `def foo(x: Optional[str] = None)` — the strict config enforces this.
