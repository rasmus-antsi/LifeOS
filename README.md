LifeOS
======

Small CLI for keeping a Mac "system" tidy and consistent by enforcing a simple filesystem spec.

Right now it focuses on *health checks* + *creating missing folders* (no destructive cleanup yet).

What It Does
------------

- Loads a local spec from `data/life-os.spec.yaml`
- Checks that key directories exist (`~/Workspace`, `~/System`, `~/Documents` by default)
- Ensures required subfolders exist for workspace, system, and documents (and can create them)

Project Layout
--------------

- `main.py` - CLI entry (argparse)
- `life_os/context.py` - loads the YAML spec + expands paths
- `life_os/app.py` - tiny command registry/dispatcher
- `commands/doctor.py` - runs checks and reports issues (no fixes)
- `commands/init.py` - creates missing folders defined by the spec
- `commands/workspace.py` - workspace checks + folder creation
- `commands/system.py` - system folder + required subfolder checks
- `commands/documents.py` - documents folder + required subfolder checks (including nested)
- `data/life-os.spec.yaml` - filesystem spec

Requirements
------------

- Python (see `pyproject.toml`)
- Dependencies in `pyproject.toml` (PyYAML, Rich, Questionary)

Run It
------

This repo ships with `uv.lock`, so using `uv` is the easiest way to run it:

```bash
uv run python main.py
```

Or with plain Python:

```bash
python3 main.py
```

Commands
--------

Doctor (default)

```bash
# Run all checks
uv run python main.py doctor

# Run a specific check
uv run python main.py doctor workspace
uv run python main.py doctor system
uv run python main.py doctor documents

# Verbose context (currently only stored on context; not all commands print more yet)
uv run python main.py --verbose doctor
```

Behavior:

- If all checks pass: exits `0`
- If any issues are found: exits `1`

Init

```bash
# Create any missing folders (workspace + system + documents)
uv run python main.py init

# Run a specific check and create what is missing
uv run python main.py init workspace
uv run python main.py init system
uv run python main.py init documents
```

Configure The Filesystem Spec
-----------------------------

Edit `data/life-os.spec.yaml`:

```yaml
filesystem:
  workspace:
    path: ~/Workspace
    required_folders:
      - code
      - clients
  system:
    path: ~/System
    required_folders:
      - apps
      - backups
  documents:
    path: ~/Documents
    required_folders:
      - school
      - files
    subfolders:
      school:
        - notes
        - assignments
```

Notes:

- Paths currently expand `~` (home directory). Environment variables like `$HOME` are not expanded yet.
- The only automatic "fix" currently implemented is creating missing folders defined in the spec.

Safety
------

- The tool currently only creates missing directories; it does not delete or move files.

What We Should Build Next
-------------------------

Practical next steps for a "keep my Mac clean" CLI, while staying safe:

- Packaging: add a proper console script entry point so `life-os` installs as a command.
- More checks: Downloads hygiene, leftover `.dmg` files, large folders, stale cache directories.
- Reporting: `--json` output and/or a non-interactive mode (fail fast in CI-style runs).
- Tests: basic unit tests for spec parsing and check results.
