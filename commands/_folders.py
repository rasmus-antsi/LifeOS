from collections.abc import Iterable
from pathlib import Path


def check_folder(
    path: Path,
    label: str,
    required_folders: Iterable[str] | None = None,
    required_subfolders: dict[str, Iterable[str]] | None = None,
) -> dict:
    if path.exists() and not path.is_dir():
        return {
            "ok": False,
            "issues": [f"{label} path is not a directory: {path}"],
            "fix": None,
        }

    required = set(required_folders or [])
    subfolders = required_subfolders or {}

    def fix():
        created: list[str] = []

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))

        if required:
            existing = {p.name for p in path.iterdir() if p.is_dir()}
            missing = sorted(required - existing)
            for name in missing:
                target = path / name
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))

        for parent, names in subfolders.items():
            parent_path = path / parent
            parent_path.mkdir(parents=True, exist_ok=True)
            existing = {p.name for p in parent_path.iterdir() if p.is_dir()}
            for name in sorted(set(names) - existing):
                target = parent_path / name
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))

        return created

    if not path.exists():
        return {
            "ok": False,
            "issues": [f"{label} directory missing: {path}"],
            "fix": fix,
        }

    if required:
        existing = {p.name for p in path.iterdir() if p.is_dir()}
        missing = sorted(required - existing)
        if missing:
            return {
                "ok": False,
                "issues": missing,
                "fix": fix,
            }

    if subfolders:
        missing_subfolders: list[str] = []
        for parent, names in subfolders.items():
            parent_path = path / parent
            if not parent_path.exists():
                missing_subfolders.append(f"{parent} (parent folder missing)")
                continue
            existing = {p.name for p in parent_path.iterdir() if p.is_dir()}
            for name in sorted(set(names) - existing):
                missing_subfolders.append(f"{parent}/{name}")

        if missing_subfolders:
            return {
                "ok": False,
                "issues": missing_subfolders,
                "fix": fix,
            }

    return {"ok": True, "issues": [], "fix": None}


def build_folder_checks(context) -> list[tuple[str, callable]]:
    fs = context.spec.get("filesystem", {})
    checks: list[tuple[str, callable]] = []

    for key, config in fs.items():
        label = key.replace("_", " ").title()
        path = Path(config["path"]).expanduser()
        required_folders = config.get("required_folders", [])
        required_subfolders = config.get("subfolders", {})

        def make_check(
            path=path,
            label=label,
            required_folders=required_folders,
            required_subfolders=required_subfolders,
        ):
            def _check(_context):
                return check_folder(
                    path=path,
                    label=label,
                    required_folders=required_folders,
                    required_subfolders=required_subfolders,
                )

            return _check

        checks.append((label, make_check()))

    return checks
