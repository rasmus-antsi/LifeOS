# Cleanup Command Plan

Goal: Add a `cleanup` command that runs **step-by-step** (Desktop → Caches → Large Files), prompts **Yes/No** at each step, and keeps output short while still indicating whether each item is likely “trash” or “might be needed.”

## Scope
- **Commands**: add `cleanup` (new), keep `doctor` and `init` unchanged.
- **Safety**: opt-in only, interactive confirmation per step, `--yes` to skip prompts, `--dry-run` always supported.
- **No destructive behavior by default**: `cleanup` is the *only* place that deletes/moves, and only after explicit confirmations.

## Spec Updates (data/life-os.spec.yaml)
- Add a `cleanup` section (version bump if needed):
  - `cleanup.desktop.allowlist` (names + patterns).
  - `cleanup.downloads.rules` (extensions, max age days, optional size thresholds).
  - `cleanup.caches.paths` (paths eligible for cleanup).
  - `cleanup.large_files.roots` + thresholds.
  - `cleanup.actions` (e.g., `trash` vs `delete`, default to `trash`).
- Reuse existing `hygiene` config when possible to avoid duplication.

## Command Design
- `cleanup` steps (in order):
  1) Desktop cleanup
  2) Caches cleanup
  3) Large files cleanup
- Each step:
  - **Detect candidates** (using allowlists and rules).
  - **Classify** each item as:
    - `trash` (e.g., old `.dmg`, `.pkg`, `.zip`, obvious temp files)
    - `might-need` (e.g., non‑installer documents, large unknown folders)
  - **Show short summary** (counts + total size + top 3 items).
  - **Prompt**: “Proceed with this step? (y/n)”
  - If yes, apply action (move to Trash by default).
  - If no, skip to next step.

## Output Style (short + clean)
- One-line per step:
  - `Desktop: 4 items (120 MB) [trash: 3, might-need: 1]`
- Optional short details:
  - Top 3 offenders only (size + name)
- After prompt:
  - `Skipped.` or `Moved to Trash: 3 items`
- Avoid verbose file lists unless `--verbose`.

## Flags
- `--dry-run`: show what *would* be cleaned, do not modify.
- `--yes`: skip prompts (still respects dry-run).
- `--verbose`: show per-path lists (otherwise short summary only).

## UX Details
- Always show: “Cleanup uses Trash by default; no permanent delete.”
- When classifying:
  - **trash**: known installers, browser downloads older than threshold.
  - **might-need**: unrecognized extensions, user documents, unknown folders.

## Implementation Notes
- New module: `commands/_cleanup.py` for detection + action functions.
- Add `commands/cleanup.py` to orchestrate steps and prompts.
- Use existing `Context` + spec, keep `doctor` as report-only.

## Acceptance Criteria
- Running `cleanup`:
  - Prompts **3 times** in order (Desktop → Caches → Large Files).
  - Each step can be skipped independently.
  - Output is short (summary + top 3 items).
  - `--dry-run` never changes filesystem.
  - `--yes` runs all steps without prompting.
  - All actions use Trash (no permanent delete).

## Tests
- Unit tests for:
  - Candidate detection per step.
  - Classification (`trash` vs `might-need`).
  - `--dry-run` produces no changes.
  - `--yes` skips prompts.
  - Summary output format (counts + size).
