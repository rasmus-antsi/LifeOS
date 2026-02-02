AGENTS.md
=========

This repo is a small Python CLI for keeping a Mac "system" organized via spec-driven checks.

High-Level Goal
---------------

Maintain a predictable folder layout and provide "doctor"-style checks that help keep a Mac clean.
For now, prefer safe operations (checks + creating missing folders). Avoid destructive cleanup unless
it is explicitly designed, confirmed, and well-tested.

Repo Map
--------

- `main.py` - CLI entry point (argparse), registers commands on `LifeOSApp`.
- `life_os/app.py` - minimal command registry + dispatcher.
- `life_os/context.py` - loads `data/life-os.spec.yaml`, exposes resolved paths on `Context`.
- `commands/doctor.py` - runs checks and optionally applies fixes.
- `commands/workspace.py` - checks workspace + creates missing required subfolders.
- `commands/system.py` - checks system folder exists.
- `commands/documents.py` - checks documents folder exists.
- `data/life-os.spec.yaml` - filesystem spec and required folders.

How To Run (dev)
----------------

Preferred:

```bash
uv run python main.py doctor
```

Alternative:

```bash
python3 main.py doctor
```

Command Design Guidelines
-------------------------

- Keep commands idempotent: running multiple times should not cause harm.
- Separate "check" and "fix":
  - `check(context) -> { ok: bool, issues: list[str], fix: Optional[callable] }`
  - `fix()` should return a list of created/changed items for printing.
- Default to non-destructive behavior. If you add cleanup, it must be:
  - Opt-in (explicit flag)
  - Confirmed (interactive unless `--yes`)
  - Logged (print what will happen; provide a dry-run)

Spec / Configuration
--------------------

The source of truth is `data/life-os.spec.yaml`.

If you add new checks, prefer extending the spec in a backwards-compatible way, e.g.:

- `filesystem.downloads.path`
- `cleanup.rules` (only if/when cleanup is introduced)

When changing the spec format:

- Bump `version` in the YAML.
- Keep migration minimal; document in `README.md`.

Output / UX
-----------

- Keep output readable in a terminal (Rich is already used).
- Always exit non-zero on unresolved issues in `doctor` so it can be used in scripts.
- Prefer flags over positional args for new functionality once it grows.

Next Work (Suggested)
---------------------

1) Packaging:
   - Add a console script entry point so `life-os` installs as a command.
2) Expand doctor checks:
   - Downloads hygiene (leftover `.dmg`, large installers)
   - Cache size reporting for `~/Library/Caches`
   - Large folder detection (top-N)
3) Reporting:
   - `--json` output for machine-readable results
4) Tests:
   - Unit tests for `Context` spec parsing and for each check module.
