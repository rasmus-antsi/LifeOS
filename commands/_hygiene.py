import re
import time
from collections import defaultdict
from pathlib import Path


def _human_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    units = ["KB", "MB", "GB", "TB", "PB"]
    size = float(value)
    for unit in units:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} EB"


def _compile_allowlist(allowlist: dict) -> tuple[set[str], list[re.Pattern]]:
    names = set(allowlist.get("names", []) or [])
    patterns = []
    for pattern in allowlist.get("patterns", []) or []:
        try:
            patterns.append(re.compile(pattern))
        except re.error:
            continue
    return names, patterns


def _is_allowed(name: str, names: set[str], patterns: list[re.Pattern]) -> bool:
    if name in names:
        return True
    return any(pattern.search(name) for pattern in patterns)


def _expand_paths(raw: str) -> list[Path]:
    expanded = Path(raw).expanduser()
    if "*" in raw or "?" in raw or "[" in raw:
        return [Path(p) for p in expanded.parent.glob(expanded.name)]
    return [expanded]


def _item_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.exists():
        return 0
    total = 0
    for root, _, files in path.walk():
        root_path = Path(root)
        for name in files:
            try:
                total += (root_path / name).stat().st_size
            except OSError:
                continue
    return total


def _dir_sizes(root: Path) -> dict[Path, int]:
    sizes: dict[Path, int] = {}
    if not root.exists():
        return sizes
    for current, dirs, files in root.walk(top_down=False):
        current_path = Path(current)
        total = 0
        for name in files:
            try:
                total += (current_path / name).stat().st_size
            except OSError:
                continue
        for name in dirs:
            total += sizes.get(current_path / name, 0)
        sizes[current_path] = total
    return sizes


def check_desktop_cleanliness(context) -> dict:
    config = context.hygiene.get("desktop", {})
    allowlist = config.get("allowlist", {})
    allowed_names, allowed_patterns = _compile_allowlist(allowlist)
    path = context.desktop

    if not path.exists():
        return {
            "ok": False,
            "issues": [f"Desktop path missing: {path}"],
            "fix": None,
            "notes": ["Report-only: no files are deleted."],
        }

    items = [
        item
        for item in path.iterdir()
        if not _is_allowed(item.name, allowed_names, allowed_patterns)
    ]

    if not items:
        return {"ok": True, "issues": [], "fix": None, "notes": []}

    issues = [f"Desktop has {len(items)} non-ignored item(s)."]
    if context.verbose:
        issues.extend(f"{item.name}" for item in sorted(items, key=lambda p: p.name))

    return {
        "ok": False,
        "issues": issues,
        "fix": None,
        "notes": ["Report-only: no files are deleted."],
    }


def check_downloads_aging(context) -> dict:
    config = context.hygiene.get("downloads", {})
    age_days = int(config.get("age_days", 7))
    top_n = int(config.get("top_n", 5))
    allowlist = config.get("allowlist", {})
    allowed_names, allowed_patterns = _compile_allowlist(allowlist)
    groups = config.get(
        "groups",
        {"dmg": [".dmg"], "pkg": [".pkg"], "zip": [".zip"]},
    )

    ext_to_group = {}
    for group, extensions in groups.items():
        for ext in extensions or []:
            ext_to_group[ext.lower()] = group

    path = context.downloads
    if not path.exists():
        return {
            "ok": False,
            "issues": [f"Downloads path missing: {path}"],
            "fix": None,
            "notes": ["Report-only: no files are deleted."],
        }

    now = time.time()
    cutoff = age_days * 24 * 60 * 60
    old_items = []
    for item in path.iterdir():
        if _is_allowed(item.name, allowed_names, allowed_patterns):
            continue
        try:
            age = now - item.stat().st_mtime
        except OSError:
            continue
        if age < cutoff:
            continue
        ext = item.suffix.lower() if item.is_file() else ""
        group = ext_to_group.get(ext, "other")
        size = _item_size(item)
        old_items.append(
            {
                "path": item,
                "group": group,
                "size": size,
                "age_days": int(age // (24 * 60 * 60)),
            }
        )

    if not old_items:
        return {"ok": True, "issues": [], "fix": None, "notes": []}

    totals = defaultdict(lambda: {"count": 0, "size": 0})
    for item in old_items:
        totals[item["group"]]["count"] += 1
        totals[item["group"]]["size"] += item["size"]

    total_count = sum(item["count"] for item in totals.values())
    total_size = sum(item["size"] for item in totals.values())

    issues = [
        f"Items older than {age_days} days: {total_count} item(s), {_human_bytes(total_size)} total.",
    ]
    for group in sorted(totals.keys()):
        group_info = totals[group]
        issues.append(
            f"{group}: {group_info['count']} item(s), {_human_bytes(group_info['size'])}."
        )

    offenders = sorted(old_items, key=lambda i: i["size"], reverse=True)
    offenders = offenders[: max(top_n, 1)]

    if context.verbose:
        for item in offenders:
            issues.append(
                f"{item['path'].name} — {_human_bytes(item['size'])}, {item['age_days']}d old."
            )
    else:
        top_summary = ", ".join(
            f"{item['path'].name} ({_human_bytes(item['size'])})" for item in offenders
        )
        if top_summary:
            issues.append(f"Top offenders: {top_summary}.")

    return {
        "ok": False,
        "issues": issues,
        "fix": None,
        "notes": ["Report-only: no files are deleted."],
    }


def check_caches_reporting(context) -> dict:
    config = context.hygiene.get("caches", {})
    warn_over_mb = int(config.get("warn_over_mb", 0))
    paths = config.get("paths", []) or []

    entries = []
    for raw in paths:
        for path in _expand_paths(raw):
            if not path.exists():
                continue
            size = _item_size(path)
            entries.append((path, size))

    if not entries:
        return {"ok": True, "issues": [], "fix": None, "notes": []}

    entries.sort(key=lambda item: item[1], reverse=True)
    issues = []
    over_threshold = False
    threshold_bytes = warn_over_mb * 1024 * 1024

    for path, size in entries:
        issues.append(f"{path}: {_human_bytes(size)}")
        if size >= threshold_bytes:
            over_threshold = True

    return {
        "ok": not over_threshold,
        "issues": issues,
        "fix": None,
        "notes": ["Report-only: no files are deleted."],
    }


def check_large_files(context) -> dict:
    config = context.hygiene.get("large_files", {})
    min_size_mb = int(config.get("min_size_mb", 250))
    top_n = int(config.get("top_n", 10))
    roots = config.get("roots", []) or []

    threshold_bytes = min_size_mb * 1024 * 1024
    candidates: list[tuple[int, str, Path]] = []

    for raw in roots:
        for root in _expand_paths(raw):
            if not root.exists():
                continue
            dir_sizes = _dir_sizes(root)
            for path, size in dir_sizes.items():
                if size >= threshold_bytes:
                    candidates.append((size, "folder", path))
            for current, _, files in root.walk():
                current_path = Path(current)
                for name in files:
                    file_path = current_path / name
                    try:
                        size = file_path.stat().st_size
                    except OSError:
                        continue
                    if size >= threshold_bytes:
                        candidates.append((size, "file", file_path))

    if not candidates:
        return {"ok": True, "issues": [], "fix": None, "notes": []}

    candidates.sort(key=lambda item: item[0], reverse=True)
    top_items = candidates[: max(top_n, 1)]

    issues = [
        f"Top {len(top_items)} item(s) over {_human_bytes(threshold_bytes)}:",
    ]
    for size, kind, path in top_items:
        issues.append(f"{kind}: {path} — {_human_bytes(size)}")

    return {
        "ok": False,
        "issues": issues,
        "fix": None,
        "notes": ["Report-only: no files are deleted."],
    }


def build_hygiene_checks(context) -> list[tuple[str, callable]]:
    return [
        ("Desktop Cleanliness", check_desktop_cleanliness),
        ("Downloads Aging", check_downloads_aging),
        ("Caches Reporting", check_caches_reporting),
        ("Large Files", check_large_files),
    ]
