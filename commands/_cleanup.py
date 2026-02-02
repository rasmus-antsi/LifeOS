import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CleanupItem:
    path: Path
    size: int
    classification: str  # "trash" | "might-need"


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


def _trash_extensions(context) -> set[str]:
    rules = context.cleanup.get("downloads", {}).get("rules", {})
    extensions = rules.get("trash_extensions", []) or []
    return {ext.lower() for ext in extensions}


def _classification_for_path(path: Path, trash_exts: set[str]) -> str:
    if path.is_file() and path.suffix.lower() in trash_exts:
        return "trash"
    return "might-need"


def desktop_candidates(context) -> list[CleanupItem]:
    config = context.cleanup.get("desktop", {})
    allowlist = config.get("allowlist", {})
    allowed_names, allowed_patterns = _compile_allowlist(allowlist)
    trash_exts = _trash_extensions(context)
    path = context.desktop

    if not path.exists():
        return []

    items: list[CleanupItem] = []
    for item in path.iterdir():
        if _is_allowed(item.name, allowed_names, allowed_patterns):
            continue
        try:
            size = _item_size(item)
        except OSError:
            continue
        classification = _classification_for_path(item, trash_exts)
        items.append(CleanupItem(path=item, size=size, classification=classification))
    return items


def downloads_candidates(context) -> list[CleanupItem]:
    config = context.cleanup.get("downloads", {})
    rules = config.get("rules", {})
    allowlist = config.get("allowlist", {})
    allowed_names, allowed_patterns = _compile_allowlist(allowlist)
    trash_exts = {ext.lower() for ext in rules.get("trash_extensions", []) or []}
    max_age_days = int(rules.get("max_age_days", 7))
    large_min_size_mb = int(rules.get("large_min_size_mb", 0))

    path = context.downloads
    if not path.exists():
        return []

    now = time.time()
    cutoff = max_age_days * 24 * 60 * 60
    size_threshold = large_min_size_mb * 1024 * 1024
    items: list[CleanupItem] = []

    for item in path.iterdir():
        if _is_allowed(item.name, allowed_names, allowed_patterns):
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        age = now - stat.st_mtime
        size = _item_size(item)
        is_old = age >= cutoff
        is_large = size_threshold > 0 and size >= size_threshold

        if not (is_old or is_large):
            continue

        classification = _classification_for_path(item, trash_exts)
        items.append(CleanupItem(path=item, size=size, classification=classification))

    return items


def caches_candidates(context) -> list[CleanupItem]:
    config = context.cleanup.get("caches", {})
    paths = config.get("paths", []) or []
    items: list[CleanupItem] = []

    for raw in paths:
        for path in _expand_paths(raw):
            if not path.exists():
                continue
            size = _item_size(path)
            items.append(CleanupItem(path=path, size=size, classification="trash"))
    return items


def large_files_candidates(context) -> list[CleanupItem]:
    config = context.cleanup.get("large_files", {})
    min_size_mb = int(config.get("min_size_mb", 250))
    roots = config.get("roots", []) or []

    threshold_bytes = min_size_mb * 1024 * 1024
    candidates: list[CleanupItem] = []

    for raw in roots:
        for root in _expand_paths(raw):
            if not root.exists():
                continue
            dir_sizes = _dir_sizes(root)
            for path, size in dir_sizes.items():
                if size >= threshold_bytes:
                    candidates.append(
                        CleanupItem(path=path, size=size, classification="might-need")
                    )
            for current, _, files in root.walk():
                current_path = Path(current)
                for name in files:
                    file_path = current_path / name
                    try:
                        size = file_path.stat().st_size
                    except OSError:
                        continue
                    if size >= threshold_bytes:
                        candidates.append(
                            CleanupItem(
                                path=file_path, size=size, classification="might-need"
                            )
                        )

    return candidates


def summarize(items: list[CleanupItem], top_n: int = 3) -> dict:
    total_size = sum(item.size for item in items)
    trash_count = sum(1 for item in items if item.classification == "trash")
    might_count = sum(1 for item in items if item.classification == "might-need")
    top_items = sorted(items, key=lambda item: item.size, reverse=True)[: max(top_n, 1)]
    return {
        "count": len(items),
        "size": total_size,
        "trash": trash_count,
        "might": might_count,
        "top": top_items,
    }


def move_to_trash(
    items: list[CleanupItem],
    trash_dir: Path,
    dry_run: bool = False,
    trash_only: bool = False,
) -> list[CleanupItem]:
    if dry_run:
        return []

    trash_dir.mkdir(parents=True, exist_ok=True)
    moved: list[CleanupItem] = []
    timestamp = int(time.time())

    for item in items:
        if trash_only and item.classification != "trash":
            continue
        if not item.path.exists():
            continue
        target = trash_dir / item.path.name
        counter = 1
        while target.exists():
            target = trash_dir / f"{item.path.name}.{timestamp}.{counter}"
            counter += 1
        try:
            shutil.move(str(item.path), str(target))
        except OSError:
            continue
        moved.append(item)
    return moved


def format_top_items(items: list[CleanupItem]) -> list[str]:
    lines = []
    for item in items:
        lines.append(f"{item.path.name} ({_human_bytes(item.size)})")
    return lines
